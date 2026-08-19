"""FastAPI app: direct-PostgreSQL source_post list/detail endpoints, gated
by OIDC login (backend.app.auth) and RBAC + ABAC (this module).

RBAC gate: the account's roles (account_role_assignment -> role_permission)
must include the 'post_read' permission at all -- a coarse yes/no on the
resource type.

ABAC gate, evaluated per row on top of the RBAC gate: a source_post is
visible if it is public, or if it is private and the requesting account is
affiliated with the post's owning corporate_entity_id. abac_policy's
condition_expression column is reserved for a future, richer per-policy
DSL (documented in migrations/0001_initial_schema.sql); Phase 1 implements
exactly this one fixed rule directly, since it is the only rule the
product currently needs.

The HTTP paths stay ``/api/posts`` (the product noun). The table they
read is ``source_post`` -- two-or-more-word table names, per AGENTS.md.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

import asyncpg
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lineageweave.commitment_extraction import (
    ContextualOrchestratorCommitmentExtractionClient,
    NullCommitmentExtractionClient,
)
from lineageweave.caldav_client import (
    CALDAV_UNAVAILABLE_NEXT_ACTION,
    build_caldav_client,
)
from lineageweave.entity_relationship_classification import (
    ContextualOrchestratorEntityRelationshipClient,
    NullEntityRelationshipClient,
)
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.embedding_client import orchestrator_embedding_client
from lineageweave.corporate_hierarchy_inference import (
    ContextualOrchestratorHierarchyInferenceClient,
    NullCorporateHierarchyInferenceClient,
)
from lineageweave.keyman_extraction import (
    ContextualOrchestratorKeymanExtractionClient,
    NullKeymanExtractionClient,
)
from lineageweave.organization_name_resolution import (
    ContextualOrchestratorOrganizationNameResolutionClient,
    NullOrganizationNameResolutionClient,
)
from lineageweave.post_chat import (
    ContextualOrchestratorPostChatClient,
    NullPostChatClient,
    cited_post_evidence,
    cited_post_summaries,
)
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_evaluation import (
    ContextualOrchestratorPostEvaluationClient,
    NullPostEvaluationClient,
    RUBRIC_VERSION,
)
from lineageweave.post_summary import ContextualOrchestratorPostSummaryClient, NullPostSummaryClient
from lineageweave.relation_verification import NullRelationVerificationClient, SearxngRelationVerificationClient
from lineageweave.semantic_hints import format_semantic_hints
from lineageweave.ontology import LW
from lineageweave.rankweave_client import build_rankweave_client

from backend.app.analysis_run_ingestion import (
    AnalysisRunCreateError,
    create_pending_analysis_run,
    fetch_visible_analysis_run,
    fetch_visible_analysis_runs,
)
from backend.app.analysis_run_outbox import publish_outbox_event
from backend.app.analysis_run_start import (
    AnalysisRunStartError,
    configured_tepp_client,
    deliver_queued_analysis_run,
    enqueue_pending_analysis_run,
)
from backend.app.analysis_run_worker import run_analysis_run_worker
from backend.app.source_post_revision import fetch_known_at_revision, parse_as_of_clock
from backend.app.activity_stream import (
    create_valkey_client,
    get_valkey,
    publish_activity_event,
    read_activity_events,
    ticket_created_summary,
    ticket_status_changed_summary,
)
from backend.app.affiliate_tree_ingestion import fetch_affiliate_forest, fetch_voc_evidence
from backend.app.auth import CurrentAccount, get_current_account
from backend.app.config import load_settings
from backend.app.db import create_pool, get_pool
from backend.app.entity_relationship_ingestion import (
    fetch_post_counterparties,
    ingest_post_entity_relationships,
)
from backend.app.five_w1h_ingestion import load_five_w1h_slots
from backend.app.post_evaluation_ingestion import fetch_post_evaluation, ingest_post_evaluation
from backend.app.ranking_ingestion import load_visible_ranking_posts
from backend.app.report_ingestion import (
    GROUPING_KINDS,
    fetch_period_comparison,
    fetch_period_reports,
    iso_week_period,
    list_period_report_summaries,
    parse_period_code,
    rebuild_period_reports,
)
from backend.app.relation_verification_ingestion import verify_post_relations
from backend.app.issue_ticket_ingestion import (
    create_ticket,
    fetch_ticket_post_id,
    fetch_upcoming_commitments,
    list_tickets_for_post,
    update_ticket,
    upsert_commitment_ticket,
)
from backend.app.keyman_ingestion import ingest_post_keymen
from backend.app.knowledge_graph import (
    corporate_entity_exists,
    fetch_post_keymen,
    labels_for_codes,
    person_exists,
    persist_edges_for_post,
    related_for_entity,
    related_for_person,
    related_for_team,
    team_exists,
    visible_affiliation_post_ids,
    visible_mention_post_ids,
    visible_team_mention_post_ids,
)
from backend.app.lineage_ingestion import rebuild_lineage, visible_lineage_graph
from backend.app.post_chat_ingestion import (
    fetch_persisted_chat,
    fetch_persisted_chats,
    find_linked_post_ids,
    gather_chat_sources,
    gather_global_chat_sources,
    persist_post_chat,
)
from backend.app.post_summary_ingestion import (
    fetch_persisted_summary,
    persist_post_summary,
    require_summary_source_body,
)
from lineageweave.post_content_persistence import persist_post_content
from lineageweave.http_client import HttpClientError

_POST_READ = "post_read"
_POST_ADMIN = "post_admin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open one asyncpg pool and one Valkey client for the process, and
    close both on shutdown."""
    settings = load_settings()
    app.state.pool = await create_pool(settings.database_url)
    app.state.valkey = create_valkey_client(settings.valkey_url)
    app.state.analysis_run_worker = asyncio.create_task(
        run_analysis_run_worker(
            app.state.valkey,
            app.state.pool,
            tepp_client=configured_tepp_client(
                settings.tepp_transport_url,
                settings.tepp_api_key,
            ),
        )
    )
    try:
        yield
    finally:
        app.state.analysis_run_worker.cancel()
        await asyncio.gather(app.state.analysis_run_worker, return_exceptions=True)
        await app.state.pool.close()
        await app.state.valkey.aclose()


app = FastAPI(title="LineageWeave API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=load_settings().frontend_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization"],
)


def _require_post_read(account: CurrentAccount) -> None:
    """Raise 403 when the account has no ``post_read`` permission at all."""
    if not account.has_permission(_POST_READ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account lacks the post_read permission")


def _require_post_admin(account: CurrentAccount) -> None:
    """Raise 403 when the account has no ``post_admin`` permission at all."""
    if not account.has_permission(_POST_ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account lacks the post_admin permission")


def _keyman_extraction_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullKeymanExtractionClient()
    return ContextualOrchestratorKeymanExtractionClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _entity_relationship_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullEntityRelationshipClient()
    return ContextualOrchestratorEntityRelationshipClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _relation_verification_client():
    """Live Searxng client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not settings.searxng_base_url:
        return NullRelationVerificationClient()
    return SearxngRelationVerificationClient(base_url=settings.searxng_base_url)


def _organization_name_resolution_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullOrganizationNameResolutionClient()
    return ContextualOrchestratorOrganizationNameResolutionClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _corporate_hierarchy_inference_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullCorporateHierarchyInferenceClient()
    return ContextualOrchestratorHierarchyInferenceClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _post_summary_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullPostSummaryClient()
    return ContextualOrchestratorPostSummaryClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _post_chat_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullPostChatClient()
    return ContextualOrchestratorPostChatClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _commitment_extraction_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullCommitmentExtractionClient()
    return ContextualOrchestratorCommitmentExtractionClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _vision_client():
    """Live vision client when configured; otherwise the unavailable null.

    Same contextual-orchestrator gateway as every other channel, plus a
    vision-capable model name (``VISION_MODEL``) -- unlike the other
    channels, a missing model name alone (base_url/api_key present but no
    model) also means unavailable, since there is no sane default model
    to guess.
    """
    settings = load_settings()
    return orchestrator_vision_client(
        settings.orchestrator_base_url,
        settings.orchestrator_api_key,
        settings.vision_model,
    )


def _embedding_client():
    """Build the orchestrator embedding client, or an unavailable channel."""
    settings = load_settings()
    return orchestrator_embedding_client(
        settings.orchestrator_base_url,
        settings.orchestrator_api_key,
        settings.embedding_model,
    )


def _post_evaluation_client():
    """Live judge client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullPostEvaluationClient()
    return ContextualOrchestratorPostEvaluationClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _rankweave_client():
    """In-process RankWeave unless RANKWEAVE_DISABLED=1 (ADR 0024)."""
    return build_rankweave_client(disabled=load_settings().rankweave_disabled)


def _can_see_post(account: CurrentAccount, post: asyncpg.Record) -> bool:
    """ABAC: public rows are visible; private rows require same-corp affiliation."""
    if post["visibility_code"] == "public":
        return True
    return str(post["corporate_entity_id"]) in account.corporate_entity_ids


def _serialize_post(post: asyncpg.Record, labels: dict[str, str] | None = None) -> dict[str, Any]:
    """Turn a ``source_post`` row into the public JSON shape."""
    resolved = labels or {}
    voc = post["voc_type_code"]
    visibility = post["visibility_code"]
    project_evidence = post.get("project_evidence") or []
    if isinstance(project_evidence, str):
        project_evidence = json.loads(project_evidence)
    return {
        "post_id": str(post["post_id"]),
        "post_title": post["post_title"],
        "voc_type_code": voc,
        "voc_type_label": resolved.get(voc, voc),
        "visibility_code": visibility,
        "visibility_label": resolved.get(visibility, visibility),
        "source_stage_code": post.get("source_stage_code"),
        "source_detail_state_code": post.get("source_detail_state_code"),
        "source_draft_code": post.get("source_draft_code"),
        "source_deleted_flag": post.get("source_deleted_flag"),
        "source_author_code": post.get("source_author_code"),
        "source_author_name": post.get("source_author_name"),
        "source_company_code": post.get("source_company_code"),
        "source_company_name": post.get("source_company_name"),
        "source_process_unit_code": post.get("source_process_unit_code"),
        "source_process_unit_name": post.get("source_process_unit_name"),
        "source_sales_pool_code": post.get("source_sales_pool_code"),
        "source_sales_pool_name": post.get("source_sales_pool_name"),
        "source_customer_code": post.get("source_customer_code"),
        "source_customer_name": post.get("source_customer_name"),
        "source_project_code": post.get("source_project_code"),
        "source_project_name": post.get("source_project_name"),
        "source_system_code": post.get("source_system_code"),
        "source_record_key": post.get("source_record_key"),
        "post_body_excerpt": post.get("post_body_excerpt"),
        "post_body_truncated": post.get("post_body_truncated", False),
        "project_evidence": project_evidence,
        "created_at": post["created_at"].isoformat(),
    }


async def _load_project_evidence(
    conn: asyncpg.Connection,
    post_id: str,
    source_project_code: str | None,
    source_project_name: str | None,
) -> list[dict[str, Any]]:
    """Merge explicit source hints and stored semantic project candidates."""
    evidence: list[dict[str, Any]] = []
    source_code = source_project_code.strip() if source_project_code else ""
    source_name = source_project_name.strip() if source_project_name else ""
    if source_code or source_name:
        source_field = (
            "source_post.source_project_name"
            if source_name
            else "source_post.source_project_code"
        )
        evidence.append(
            {
                "project_key": source_code or source_name,
                "project_name": source_name or source_code,
                "evidence": source_field,
                "confidence": None,
                "ontology_iri": str(LW.Project),
                "ontology_label": "Project",
                "extraction_method": "source_field_hint",
                "resolution_status": "hint_only",
                "provenance": source_field,
            }
        )
    rows = await conn.fetch(
        """
        select project_key, project_name, evidence_text, confidence,
               ontology_iri, extraction_method
          from post_project_mention
         where post_id = $1
         order by confidence desc, project_name, project_key
        """,
        post_id,
    )
    evidence.extend(
        {
            "project_key": row["project_key"],
            "project_name": row["project_name"],
            "evidence": row["evidence_text"],
            "confidence": float(row["confidence"]),
            "ontology_iri": row["ontology_iri"],
            "ontology_label": "Project",
            "extraction_method": row["extraction_method"],
            "resolution_status": "semantic_candidate",
            "provenance": "post_project_mention.evidence_text",
        }
        for row in rows
    )
    return evidence


async def _lookup_post_labels(conn: asyncpg.Connection, rows: list[asyncpg.Record]) -> dict[str, str]:
    """Resolve voc_type / visibility codes against common_lookup_value."""
    codes = [row["voc_type_code"] for row in rows] + [row["visibility_code"] for row in rows]
    return await labels_for_codes(conn, codes)


async def _post_filter_options(
    conn: asyncpg.Connection, corporate_entity_ids: frozenset[str]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return every authorized filter value, not only values on the current page."""
    visibility_sql = """
        select distinct post.visibility_code as code,
               coalesce(lookup.lookup_label, post.visibility_code) as label,
               coalesce(lookup.display_order, 2147483647) as display_order
          from source_post post
          left join common_lookup_value lookup
            on lookup.lookup_category = 'post_visibility'
           and lookup.lookup_code = post.visibility_code
         where (post.visibility_code = 'public'
            or post.corporate_entity_id::text = any($1::text[]))
         order by display_order, code
    """
    type_sql = """
        select distinct post.voc_type_code as code,
               coalesce(lookup.lookup_label, post.voc_type_code) as label,
               coalesce(lookup.display_order, 2147483647) as display_order
          from source_post post
          left join common_lookup_value lookup
            on lookup.lookup_category = 'voc_type'
           and lookup.lookup_code = post.voc_type_code
         where (post.visibility_code = 'public'
            or post.corporate_entity_id::text = any($1::text[]))
         order by display_order, code
    """
    visibility_rows = await conn.fetch(visibility_sql, list(corporate_entity_ids))
    type_rows = await conn.fetch(type_sql, list(corporate_entity_ids))
    return (
        [{"code": row["code"], "label": row["label"]} for row in type_rows],
        [{"code": row["code"], "label": row["label"]} for row in visibility_rows],
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe: the process is up. Does not touch Postgres."""
    return {"status": "ok"}


@app.get("/api/me")
async def read_me(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Return the provisioned account and the corps this token may walk.

    Multi-affiliation operators need those names to choose which entity
    ``POST /api/analysis-runs`` should cover.
    """
    entities: list[dict[str, str]] = []
    if account.corporate_entity_ids:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                select corporate_entity_id, entity_name
                  from corporate_entity
                 where corporate_entity_id = any($1::uuid[])
                 order by entity_name
                """,
                list(account.corporate_entity_ids),
            )
        entities = [
            {
                "corporate_entity_id": str(row["corporate_entity_id"]),
                "entity_name": row["entity_name"],
            }
            for row in rows
        ]
    return {
        "user_account_id": account.user_account_id,
        "display_name": account.display_name,
        "permission_codes": sorted(account.permission_codes),
        "corporate_entities": entities,
    }


@app.get("/api/customer-master")
async def read_customer_master(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Return the authorized customer catalog and its cataloged Keymen."""
    _require_post_read(account)
    if not account.corporate_entity_ids:
        return {
            "corporate_entities": [],
            "keymen": [],
            "source_customer_hints": [],
            "source_author_hints": [],
        }

    async with pool.acquire() as conn:
        source_customer_rows = await conn.fetch(
            """
            with scoped as (
                select post_id, post_title, created_at,
                       nullif(btrim(source_customer_code), '') as customer_code,
                       nullif(btrim(source_customer_name), '') as customer_name,
                       case when nullif(btrim(source_customer_code), '') is null
                            then nullif(btrim(source_customer_name), '')
                            else null end as customer_name_group
                  from source_post
                 where (nullif(btrim(source_customer_code), '') is not null
                        or nullif(btrim(source_customer_name), '') is not null)
                   and (visibility_code = 'public' or corporate_entity_id = any($1::uuid[]))
            ), ranked as (
                select scoped.*,
                       row_number() over (
                           partition by customer_code, customer_name_group
                           order by created_at desc, post_id desc
                       ) as related_rank
                  from scoped
            ), groups as (
                select customer_code, customer_name_group,
                       max(customer_name) as customer_name,
                       count(*) as post_count
                  from ranked
                 group by customer_code, customer_name_group
            ), related as (
                select ranked.customer_code, ranked.customer_name_group,
                       json_agg(
                           json_build_object(
                               'post_id', post.post_id::text,
                               'post_title', post.post_title,
                               'post_body_excerpt', btrim(left(source_post_search_text(post.post_body), 420)),
                               'post_body_truncated', char_length(coalesce(post.post_body, '')) > 420
                           )
                           order by ranked.created_at desc, ranked.post_id desc
                       ) as related_posts
                  from ranked
                  join source_post post on post.post_id = ranked.post_id
                 where ranked.related_rank <= 20
                 group by ranked.customer_code, ranked.customer_name_group
            )
            select groups.customer_code, groups.customer_name, groups.post_count,
                   coalesce(related.related_posts, '[]'::json) as related_posts
              from groups
              left join related
                on related.customer_code is not distinct from groups.customer_code
               and related.customer_name_group is not distinct from groups.customer_name_group
             order by groups.post_count desc, groups.customer_code, groups.customer_name
             limit 100
            """,
            list(account.corporate_entity_ids),
        )
        source_author_rows = await conn.fetch(
            """
            with scoped as (
                select post.post_id, post.post_title, post.created_at,
                       btrim(post.source_author_code) as author_code,
                       case
                           when post.source_author_name is null
                             or btrim(post.source_author_name) = ''
                             or lower(btrim(post.source_author_name)) = lower(btrim(post.source_author_code))
                           then null
                           else btrim(post.source_author_name)
                       end as source_author_name,
                       post.author_account_id,
                       author.display_name as account_display_name
                  from source_post post
                  join user_account author on author.user_account_id = post.author_account_id
                 where post.source_author_code is not null
                   and btrim(post.source_author_code) <> ''
                   and (post.visibility_code = 'public' or post.corporate_entity_id = any($1::uuid[]))
            ), ranked as (
                select scoped.*,
                       row_number() over (
                           partition by author_code, author_account_id, account_display_name
                           order by created_at desc, post_id desc
                       ) as related_rank
                  from scoped
            ), groups as (
                select author_code, author_account_id, account_display_name,
                       max(source_author_name) as author_name,
                       count(*) as post_count
                  from ranked
                 group by author_code, author_account_id, account_display_name
            ), keyman_groups as (
                select ranked.author_code, ranked.author_account_id,
                       ranked.account_display_name,
                       person.person_id, person.person_name,
                       person.person_side_code, person.last_known_job_title,
                       count(distinct ranked.post_id) as mention_count
                  from ranked
                  join post_summary_role role
                    on role.post_id = ranked.post_id
                   and role.actor_type_code = 'prov_person'
                  join cataloged_person person
                    on person.person_id = role.cataloged_person_id
                   and person.person_side_code = 'our_side'
                 where role.cataloged_person_id is not null
                 group by ranked.author_code, ranked.author_account_id,
                          ranked.account_display_name, person.person_id,
                          person.person_name, person.person_side_code,
                          person.last_known_job_title
            ), keyman_related as (
                select author_code, author_account_id, account_display_name,
                       json_agg(
                           json_build_object(
                               'person_id', person_id::text,
                               'person_name', person_name,
                               'person_side_code', person_side_code,
                               'last_known_job_title', last_known_job_title,
                               'mention_count', mention_count,
                               'provenance',
                               'post_summary_role.cataloged_person_id/source_post.author_account_id'
                           )
                           order by mention_count desc, person_name, person_id
                       ) as keyman_hints
                  from keyman_groups
                 group by author_code, author_account_id, account_display_name
            ), related as (
                select ranked.author_code, ranked.author_account_id, ranked.account_display_name,
                       json_agg(
                           json_build_object(
                               'post_id', post.post_id::text,
                               'post_title', post.post_title,
                               'post_body_excerpt', btrim(left(source_post_search_text(post.post_body), 420)),
                               'post_body_truncated', char_length(coalesce(post.post_body, '')) > 420
                           )
                           order by ranked.created_at desc, ranked.post_id desc
                       ) as related_posts
                  from ranked
                  join source_post post on post.post_id = ranked.post_id
                 where ranked.related_rank <= 20
                 group by ranked.author_code, ranked.author_account_id, ranked.account_display_name
            )
            select groups.author_code, groups.author_name, groups.author_account_id,
                   groups.account_display_name, groups.post_count,
                   coalesce(keyman_related.keyman_hints, '[]'::json) as keyman_hints,
                   coalesce(related.related_posts, '[]'::json) as related_posts
              from groups
              left join keyman_related
                on keyman_related.author_code = groups.author_code
               and keyman_related.author_account_id = groups.author_account_id
               and keyman_related.account_display_name = groups.account_display_name
              left join related
                on related.author_code = groups.author_code
               and related.author_account_id = groups.author_account_id
               and related.account_display_name = groups.account_display_name
             order by groups.post_count desc, groups.author_code
             limit 100
            """,
            list(account.corporate_entity_ids),
        )
        entity_rows = await conn.fetch(
            """
            select corporate_entity_id, corporate_entity_code, entity_name,
                   entity_level_code, parent_entity_id
              from corporate_entity
             where corporate_entity_id = any($1::uuid[])
             order by entity_name
            """,
            list(account.corporate_entity_ids),
        )
        has_source_context = bool(source_customer_rows or source_author_rows)
        if not has_source_context:
            has_source_context = bool(
                await conn.fetchval(
                    """
                    select exists (
                        select 1
                          from source_post
                         where (visibility_code = 'public'
                                or corporate_entity_id = any($1::uuid[]))
                           and (
                                nullif(btrim(source_author_code), '') is not null
                                or nullif(btrim(source_author_name), '') is not null
                                or nullif(btrim(source_company_code), '') is not null
                                or nullif(btrim(source_company_name), '') is not null
                                or nullif(btrim(source_process_unit_code), '') is not null
                                or nullif(btrim(source_process_unit_name), '') is not null
                                or nullif(btrim(source_sales_pool_code), '') is not null
                                or nullif(btrim(source_sales_pool_name), '') is not null
                                or nullif(btrim(source_customer_code), '') is not null
                                or nullif(btrim(source_customer_name), '') is not null
                                or nullif(btrim(source_project_code), '') is not null
                                or nullif(btrim(source_project_name), '') is not null
                           )
                    )
                    """,
                    list(account.corporate_entity_ids),
                )
            )
        if has_source_context:
            entity_rows = [
                row
                for row in entity_rows
                if not str(row["corporate_entity_code"]).startswith("DEMO-")
            ]
        entity_ids = [row["corporate_entity_id"] for row in entity_rows]
        source_author_affiliations = await _load_account_affiliation_hints(
            conn,
            [str(row["author_account_id"]) for row in source_author_rows],
            [str(entity_id) for entity_id in entity_ids],
        )
        keyman_rows = await conn.fetch(
            """
            select person.person_id, person.person_name, person.person_side_code,
                   person.last_known_job_title,
                   affiliation.affiliated_organization_name,
                   affiliation.affiliated_corporate_entity_id,
                   affiliation.role_title,
                   entity.entity_name
              from cataloged_person person
              join person_affiliation affiliation on affiliation.person_id = person.person_id
              left join corporate_entity entity
                on entity.corporate_entity_id = affiliation.affiliated_corporate_entity_id
             where affiliation.affiliated_corporate_entity_id = any($1::uuid[])
             order by person.person_name, affiliation.affiliated_organization_name
            """,
            entity_ids,
        )

    keymen_by_id: dict[str, dict[str, Any]] = {}
    for row in keyman_rows:
        person_id = str(row["person_id"])
        keyman = keymen_by_id.setdefault(
            person_id,
            {
                "person_id": person_id,
                "person_name": row["person_name"],
                "person_side_code": row["person_side_code"],
                "last_known_job_title": row["last_known_job_title"],
                "affiliations": [],
            },
        )
        keyman["affiliations"].append(
            {
                "organization_name": row["affiliated_organization_name"],
                "corporate_entity_id": (
                    str(row["affiliated_corporate_entity_id"])
                    if row["affiliated_corporate_entity_id"] is not None
                    else None
                ),
                "entity_name": row["entity_name"],
                "role_title": row["role_title"],
            }
        )

    return {
        "corporate_entities": [
            {
                "corporate_entity_id": str(row["corporate_entity_id"]),
                "corporate_entity_code": row["corporate_entity_code"],
                "entity_name": row["entity_name"],
                "entity_level_code": row["entity_level_code"],
                "parent_entity_id": (
                    str(row["parent_entity_id"]) if row["parent_entity_id"] is not None else None
                ),
            }
            for row in entity_rows
        ],
        "keymen": list(keymen_by_id.values()),
        "source_customer_hints": [
            {
                "customer_code": row["customer_code"],
                "customer_name": row["customer_name"],
                "post_count": row["post_count"],
                "related_posts": (
                    json.loads(row["related_posts"])
                    if isinstance(row["related_posts"], str)
                    else row["related_posts"] or []
                ),
                "resolution_status": "hint_only",
                "provenance": "source_post.source_customer_code/source_post.source_customer_name",
            }
            for row in source_customer_rows
        ],
        "source_author_hints": [
            {
                "author_code": row["author_code"],
                "author_name": row["author_name"],
                "author_account_id": str(row["author_account_id"]),
                "account_display_name": row["account_display_name"],
                "account_affiliations": source_author_affiliations.get(
                    str(row["author_account_id"]), []
                ),
                "post_count": row["post_count"],
                "keyman_hints": (
                    json.loads(row["keyman_hints"])
                    if isinstance(row["keyman_hints"], str)
                    else row["keyman_hints"] or []
                ),
                "related_posts": (
                    json.loads(row["related_posts"])
                    if isinstance(row["related_posts"], str)
                    else row["related_posts"] or []
                ),
                "resolution_status": (
                    "our_side_context_only"
                    if source_author_affiliations.get(str(row["author_account_id"]), [])
                    else "source_author_hint_only"
                ),
                "provenance": (
                    "source_post.author_account_id/user_account.display_name/"
                    "account_affiliation.corporate_entity_id/source_post.source_author_code/source_post.source_author_name"
                ),
            }
            for row in source_author_rows
        ],
    }


@app.get("/api/lineage")
async def read_lineage_graph(
    limit: int = Query(500, ge=1, le=2000),
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """ABAC-filtered reconstruct graph bounded for browser rendering."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        return await visible_lineage_graph(
            conn,
            lambda row: _can_see_post(account, row),
            limit=limit,
        )


@app.post("/api/lineage/rebuild")
async def rebuild_lineage_graph(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Run reconstruct over every source_post and persist post_lineage_edge.

    post_admin only: this is a corpus-wide write. Reads stay ABAC-gated.
    """
    _require_post_admin(account)
    async with pool.acquire() as conn:
        async with conn.transaction():
            edges = await rebuild_lineage(conn)
    return {"edge_count": len(edges)}


@app.get("/api/posts")
async def list_posts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    voc_type: str | None = Query(None, max_length=80),
    visibility: str | None = Query(None, max_length=80),
    sort: Literal["newest", "oldest", "title"] = Query("newest"),
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """List authorized posts, with semantic evidence search when requested."""
    _require_post_read(account)
    search_term = search.strip() if search and search.strip() else None
    async with pool.acquire() as conn:
        voc_type_options, visibility_options = await _post_filter_options(
            conn, account.corporate_entity_ids
        )
        body_search_ids: list[str] = []
        if search_term:
            body_rows = await conn.fetch(
                """
                select post_id
                  from source_post
                where lower(left(source_post_search_text(post_body), 16384))
                           like '%' || lower($1) || '%'
                    or to_tsvector('simple', source_post_search_text(post_body))
                           @@ plainto_tsquery('simple', $1)
                """,
                search_term,
            )
            body_search_ids = [str(row["post_id"]) for row in body_rows]
        rows = await conn.fetch(
            """
            with page as (
                select post.post_id, post.post_title, post.voc_type_code, post.visibility_code,
                       post.source_stage_code, post.source_detail_state_code,
                       post.source_draft_code, post.source_deleted_flag,
                       post.source_author_code, post.source_author_name,
                       post.source_company_code, post.source_company_name,
                       post.source_process_unit_code, post.source_process_unit_name,
                       post.source_sales_pool_code, post.source_sales_pool_name,
                       post.source_customer_code, post.source_customer_name,
                       post.source_project_code, post.source_project_name,
                       post.source_system_code,
                       post.source_record_key,
                       post.corporate_entity_id, post.created_at,
                       count(*) over() as total_count
                  from source_post post
             where (post.visibility_code = 'public'
                or post.corporate_entity_id::text = any($2::text[]))
               and (
                    $1::text is null
                    or post.post_title ilike '%' || $1 || '%'
                    or post.thread_group_key ilike '%' || $1 || '%'
                    or post.secondary_grouping_key ilike '%' || $1 || '%'
                    or concat_ws(' ',
                        post.source_stage_code,
                        post.source_detail_state_code,
                        post.source_draft_code,
                        post.source_deleted_flag,
                        post.source_author_code,
                        post.source_author_name,
                        post.source_company_code,
                        post.source_company_name,
                        post.source_process_unit_code,
                        post.source_process_unit_name,
                        post.source_sales_pool_code,
                        post.source_sales_pool_name,
                        post.source_customer_code,
                        post.source_customer_name,
                        post.source_project_code,
                        post.source_project_name,
                        post.source_system_code,
                        post.source_record_key
                    ) ilike '%' || $1 || '%'
                    or replace(post.post_id::text, '-', '') ilike '%' || lower($1) || '%'
                    or (
                        char_length($1) >= 3
                        and (
                            similarity(replace(post.post_id::text, '-', ''), lower($1)) >= 0.78
                            or similarity(lower(coalesce(post.source_record_key, '')), lower($1)) >= 0.78
                            or word_similarity(lower($1), lower(post.post_title)) >= 0.45
                            or word_similarity(lower($1), lower(post.secondary_grouping_key)) >= 0.45
                            or word_similarity(
                                lower($1),
                                lower(concat_ws(' ',
                                    post.source_stage_code,
                                    post.source_detail_state_code,
                                    post.source_draft_code,
                                    post.source_deleted_flag,
                                    post.source_author_code,
                                    post.source_author_name,
                                    post.source_company_code,
                                    post.source_company_name,
                                    post.source_process_unit_code,
                                    post.source_process_unit_name,
                                    post.source_sales_pool_code,
                                    post.source_sales_pool_name,
                                    post.source_customer_code,
                                    post.source_customer_name,
                                    post.source_project_code,
                                    post.source_project_name
                                ))
                            ) >= 0.45
                        )
                    )
                    or post.post_id = any($5::uuid[])
                    or exists (
                        select 1 from post_project_mention project
                         where project.post_id = post.post_id
                           and (project.project_name ilike '%' || $1 || '%'
                                or project.evidence_text ilike '%' || $1 || '%'
                                or project.ontology_iri ilike '%' || $1 || '%'
                                or (char_length($1) >= 3 and word_similarity(lower($1), lower(project.project_name)) >= 0.45))
                    )
                    or exists (
                        select 1 from post_summary_role role
                         where role.post_id = post.post_id
                           and (role.actor_name ilike '%' || $1 || '%'
                                or role.responsibility ilike '%' || $1 || '%'
                                or coalesce(role.affiliated_organization_name, '') ilike '%' || $1 || '%'
                                or (char_length($1) >= 3 and word_similarity(lower($1), lower(role.actor_name)) >= 0.45))
                    )
                    or exists (
                        select 1
                          from post_person_mention mention
                          join cataloged_person person on person.person_id = mention.person_id
                         where mention.post_id = post.post_id
                           and (
                               person.person_name ilike '%' || $1 || '%'
                               or (char_length($1) >= 3 and word_similarity(lower($1), lower(person.person_name)) >= 0.45)
                           )
                    )
                    or exists (
                        select 1 from post_summary_result summary
                         where summary.post_id = post.post_id
                           and summary.korean_summary ilike '%' || $1 || '%'
                    )
                    or exists (
                        select 1 from post_summary_event event
                         where event.post_id = post.post_id
                           and event.event_text ilike '%' || $1 || '%'
                    )
                    or exists (
                        select 1 from corporate_entity customer
                         where customer.corporate_entity_id = post.corporate_entity_id
                           and (customer.entity_name ilike '%' || $1 || '%'
                                or customer.corporate_entity_code ilike '%' || $1 || '%')
                    )
                    or exists (
                        select 1 from process_unit process
                         where process.process_unit_id = post.process_unit_id
                           and (process.process_unit_name ilike '%' || $1 || '%'
                                or process.process_unit_code ilike '%' || $1 || '%')
                    )
                    or exists (
                        select 1 from user_account author
                         where author.user_account_id = post.author_account_id
                           and (author.display_name ilike '%' || $1 || '%'
                                or author.email_address ilike '%' || $1 || '%')
                    )
                    or exists (
                        select 1
                          from account_affiliation affiliation
                          join corporate_entity affiliated
                            on affiliated.corporate_entity_id = affiliation.corporate_entity_id
                         where affiliation.user_account_id = post.author_account_id
                           and (affiliated.entity_name ilike '%' || $1 || '%'
                                or affiliated.corporate_entity_code ilike '%' || $1 || '%')
                    )
               )
               and ($3::text is null or post.voc_type_code = $3)
               and ($4::text is null or post.visibility_code = $4)
                 order by
                    case when $8::text = 'title' then lower(coalesce(post.post_title, '')) end asc,
                    case when $8::text = 'oldest' then post.created_at end asc,
                    case when $8::text in ('newest', 'title') then post.created_at end desc,
                    post.post_id desc
                   offset $6
                   limit $7
            )
            select page.*,
                   btrim(left(source_post_search_text(post.post_body), 420)) as post_body_excerpt,
                   char_length(coalesce(post.post_body, '')) > 420 as post_body_truncated,
                   coalesce(projects.project_evidence, '[]'::json) as project_evidence
              from page
              join source_post post on post.post_id = page.post_id
              left join lateral (
                  select json_agg(
                             json_build_object(
                                 'project_key', project.project_key,
                                 'project_name', project.project_name,
                                 'evidence', project.evidence_text,
                                 'confidence', project.confidence,
                                 'ontology_iri', project.ontology_iri,
                                 'ontology_label', 'Project',
                                 'extraction_method', project.extraction_method,
                                 'resolution_status', 'semantic_candidate',
                                 'provenance', 'post_project_mention.evidence_text'
                             )
                             order by project.confidence desc, project.project_name, project.project_key
                         ) as project_evidence
                    from (
                        select project_key, project_name, evidence_text, confidence,
                               ontology_iri, extraction_method
                          from post_project_mention
                         where post_id = page.post_id
                         order by confidence desc, project_name, project_key
                         limit 5
                    ) project
              ) projects on true
             order by
                case when $8::text = 'title' then lower(coalesce(page.post_title, '')) end asc,
                case when $8::text = 'oldest' then page.created_at end asc,
                case when $8::text in ('newest', 'title') then page.created_at end desc,
                page.post_id desc
            """,
            search_term,
            list(account.corporate_entity_ids),
            voc_type.strip() if voc_type and voc_type.strip() else None,
            visibility.strip() if visibility and visibility.strip() else None,
            body_search_ids,
            offset,
            limit,
            sort,
        )
        visible = [row for row in rows if _can_see_post(account, row)]
        labels = await _lookup_post_labels(conn, visible)
    total_count = int(rows[0]["total_count"]) if rows else 0
    return {
        "posts": [_serialize_post(row, labels) for row in visible],
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "voc_type_options": voc_type_options,
        "visibility_options": visibility_options,
    }


@app.get("/api/posts/{post_id}")
async def read_post(
    post_id: str,
    as_of: str | None = None,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Return one source_post, or 404 / 403 if it is missing or out of scope.

    ``as_of`` adds ``known_at`` when a ``source_post_revision`` covers that
    clock (ADR 0025). The live ``post_body`` stays the live row. A missing
    cover is omitted -- never a fabricated cutoff sentence. Next action:
    pass the analysis-run cutoff, then compare ``known_at`` with the live
    body before treating the live text as reconstructed evidence.
    """
    _require_post_read(account)
    as_of_clock = None
    if as_of is not None:
        try:
            as_of_clock = parse_as_of_clock(as_of)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "as_of must be an ISO-8601 timestamp. Use the run cutoff, "
                "then compare the known body with the live body.",
            ) from exc
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select post_id, post_title, post_body, voc_type_code, visibility_code, "
            "source_stage_code, source_detail_state_code, source_draft_code, source_deleted_flag, "
                "source_author_code, source_author_name, source_company_code, source_company_name, "
                "source_process_unit_code, source_process_unit_name, "
                "source_sales_pool_code, source_sales_pool_name, "
                "source_customer_code, source_customer_name, source_project_code, source_project_name, "
                "source_system_code, source_record_key, "
            "corporate_entity_id, created_at "
            "from source_post where post_id = $1",
            post_id,
        )
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "post not found")
        if not _can_see_post(account, row):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized to view this post")
        labels = await _lookup_post_labels(conn, [row])
        project_evidence = await _load_project_evidence(
            conn, post_id, row["source_project_code"], row["source_project_name"]
        )
        known_at = None
        if as_of_clock is not None:
            known_at = await fetch_known_at_revision(conn, post_id, as_of_clock)
    payload = {
        **_serialize_post(row, labels),
        "post_body": row["post_body"],
        "project_evidence": project_evidence,
    }
    if known_at is not None:
        payload["known_at"] = known_at
    return payload


async def _load_visible_post(
    post_id: str,
    account: CurrentAccount,
    pool: asyncpg.Pool,
) -> asyncpg.Record:
    """Load one post the account may see, or raise 404 / 403."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select post_id, post_title, voc_type_code, visibility_code, corporate_entity_id, created_at "
            "from source_post where post_id = $1",
            post_id,
        )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "post not found")
    if not _can_see_post(account, row):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized to view this post")
    return row


async def _load_post_semantic_hints(conn: asyncpg.Connection, post_id: str) -> str:
    """Render author, business-unit, sales-pool, and customer hints without treating them as proof."""
    rows = await conn.fetch(
        """
        select author.user_account_id as author_account_id,
               author.display_name as author_name,
               post.source_author_code,
               post.source_author_name,
               post.source_company_code,
               post.source_company_name,
               post.source_process_unit_code,
               post.source_process_unit_name,
               post.source_sales_pool_code,
               post.source_sales_pool_name,
               post.source_customer_code,
               post.source_customer_name,
               post.source_project_code,
               post.source_project_name,
               post.secondary_grouping_key as project_field,
               customer.entity_name as customer_name,
               affiliated.entity_name as author_affiliation_name
          from source_post post
          join user_account author on author.user_account_id = post.author_account_id
          left join corporate_entity customer on customer.corporate_entity_id = post.corporate_entity_id
          left join account_affiliation account_aff
            on account_aff.user_account_id = post.author_account_id
          left join corporate_entity affiliated
            on affiliated.corporate_entity_id = account_aff.corporate_entity_id
         where post.post_id = $1
        """,
        post_id,
    )
    if not rows:
        return "no structured hints available"
    first = rows[0]
    source_context_present = any(
        first[field] is not None
        for field in (
            "source_author_code",
            "source_author_name",
            "source_company_code",
            "source_company_name",
            "source_process_unit_code",
            "source_process_unit_name",
            "source_sales_pool_code",
            "source_sales_pool_name",
            "source_customer_code",
            "source_customer_name",
            "source_project_code",
            "source_project_name",
        )
    )
    source_author_name = first["source_author_name"]
    if source_author_name and source_author_name == first["source_author_code"]:
        source_author_name = None
    return format_semantic_hints(
        author_name=source_author_name or first["author_name"],
        author_account_id=str(first["author_account_id"]),
        author_account_name=first["author_name"],
        author_affiliations=(
            str(row["author_affiliation_name"])
            for row in rows
            if row["author_affiliation_name"]
        ),
        order_pool_code=first["source_sales_pool_code"],
        order_pool_name=first["source_sales_pool_name"],
        project_field=first["project_field"],
        customer_name=first["customer_name"],
        source_author_code=first["source_author_code"],
        source_author_name=source_author_name,
        source_company_code=first["source_company_code"],
        source_company_name=first["source_company_name"],
        source_business_unit_code=first["source_process_unit_code"],
        source_process_unit_name=first["source_process_unit_name"],
        source_sales_pool_code=first["source_sales_pool_code"],
        source_sales_pool_name=first["source_sales_pool_name"],
        source_customer_code=first["source_customer_code"],
        source_customer_name=first["source_customer_name"],
        source_project_code=first["source_project_code"],
        source_project_name=first["source_project_name"],
        source_context_present=source_context_present,
    )


async def _load_account_affiliation_hints(
    conn: asyncpg.Connection,
    account_ids: list[str],
    corporate_entity_ids: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """Load authorized account affiliations as non-binding Keyman context."""
    if not account_ids or not corporate_entity_ids:
        return {}
    rows = await conn.fetch(
        """
        select affiliation.user_account_id,
               entity.corporate_entity_id,
               entity.entity_name,
               process.process_unit_code,
               process.process_unit_name
          from account_affiliation affiliation
          join corporate_entity entity
            on entity.corporate_entity_id = affiliation.corporate_entity_id
          left join process_unit process
            on process.process_unit_id = affiliation.process_unit_id
         where affiliation.user_account_id = any($1::uuid[])
           and affiliation.corporate_entity_id = any($2::uuid[])
         order by entity.entity_name, process.process_unit_code
        """,
        account_ids,
        corporate_entity_ids,
    )
    affiliations: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        account_id = str(row["user_account_id"])
        affiliations.setdefault(account_id, []).append(
            {
                "corporate_entity_id": str(row["corporate_entity_id"]),
                "entity_name": row["entity_name"],
                "process_unit_code": row["process_unit_code"],
                "process_unit_name": row["process_unit_name"],
            }
        )
    return affiliations


async def _load_source_author_context(
    conn: asyncpg.Connection,
    post_id: str,
    corporate_entity_ids: list[str],
) -> dict[str, Any] | None:
    """Return source-author/account context without binding a cataloged person."""
    row = await conn.fetchrow(
        """
        select post.author_account_id,
               author.display_name as account_display_name,
               nullif(btrim(post.source_author_code), '') as source_author_code,
               nullif(btrim(post.source_author_name), '') as source_author_name
          from source_post post
          join user_account author on author.user_account_id = post.author_account_id
         where post.post_id = $1
        """,
        post_id,
    )
    if row is None:
        return None
    account_id = str(row["author_account_id"])
    affiliations = (
        await _load_account_affiliation_hints(conn, [account_id], corporate_entity_ids)
    ).get(account_id, [])
    source_author_name = row["source_author_name"]
    if source_author_name and source_author_name.casefold() == str(row["source_author_code"] or '').casefold():
        source_author_name = None
    return {
        "author_account_id": account_id,
        "account_display_name": row["account_display_name"],
        "source_author_code": row["source_author_code"],
        "source_author_name": source_author_name,
        "account_affiliations": affiliations,
        "resolution_status": (
            "our_side_context_only" if affiliations else "source_author_hint_only"
        ),
        "provenance": (
            "source_post.author_account_id/user_account.display_name/"
            "account_affiliation.corporate_entity_id/source_post.source_author_code/source_post.source_author_name"
        ),
    }


@app.get("/api/posts/{post_id}/keymen")
async def read_post_keymen(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """People mentioned on one visible post, with their N:N affiliations."""
    post = await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        keymen = await fetch_post_keymen(conn, post_id)
        source_author_context = await _load_source_author_context(
            conn, post_id, list(account.corporate_entity_ids)
        )
    return {
        "post_id": str(post["post_id"]),
        "keymen": keymen,
        "source_author_context": source_author_context,
    }


@app.get("/api/keymen/{person_id}/related")
async def read_related_keymen(
    person_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """RWR-ranked related nodes from one person, hiding unseen posts."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        if not await person_exists(conn, person_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "person not found")
        visible_post_ids = await visible_mention_post_ids(conn, person_id, lambda row: _can_see_post(account, row))
        if not visible_post_ids:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized to view this person")
        person = await conn.fetchrow(
            "select person_id, person_name, person_side_code from cataloged_person where person_id = $1",
            person_id,
        )
        related = await related_for_person(conn, person_id, visible_post_ids)
    return {
        "person_id": str(person["person_id"]),
        "person_name": person["person_name"],
        "person_side_code": person["person_side_code"],
        "related": related,
    }


@app.get("/api/corporate-entities/{entity_id}/related")
async def read_related_corporate_entity(
    entity_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """RWR-ranked related nodes from one corporate entity, hiding unseen posts."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        if not await corporate_entity_exists(conn, entity_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "corporate entity not found")
        visible_post_ids = await visible_affiliation_post_ids(
            conn, entity_id, lambda row: _can_see_post(account, row)
        )
        if not visible_post_ids:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized to view this entity")
        entity = await conn.fetchrow(
            "select corporate_entity_id, entity_name from corporate_entity "
            "where corporate_entity_id = $1",
            entity_id,
        )
        related = await related_for_entity(conn, entity_id, visible_post_ids)
    return {
        "corporate_entity_id": str(entity["corporate_entity_id"]),
        "entity_name": entity["entity_name"],
        "related": related,
    }


@app.get("/api/teams/{team_id}/related")
async def read_related_team(
    team_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """RWR-ranked related nodes from one cataloged team, hiding unseen posts."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        if not await team_exists(conn, team_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "team not found")
        visible_post_ids = await visible_team_mention_post_ids(
            conn, team_id, lambda row: _can_see_post(account, row)
        )
        if not visible_post_ids:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized to view this team")
        team = await conn.fetchrow(
            "select team_id, team_name from cataloged_team where team_id = $1",
            team_id,
        )
        related = await related_for_team(conn, team_id, visible_post_ids)
    return {
        "team_id": str(team["team_id"]),
        "team_name": team["team_name"],
        "related": related,
    }


@app.get("/api/posts/{post_id}/counterparties")
async def read_post_counterparties(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Classified counterparty orgs for one visible post.

    A name that resolves to a cataloged ``corporate_entity`` carries
    that id so the popup can start the same related walk as an
    affiliate-tree org click. Unresolved names stay ``null``.
    """
    post = await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        counterparties = await fetch_post_counterparties(conn, post_id)
    return {
        "post_id": str(post["post_id"]),
        "counterparties": counterparties,
    }


@app.get("/api/posts/{post_id}/affiliate-tree")
async def read_post_affiliate_tree(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Ancestor forest of every organization this post's Keymen touch.

    Resolved affiliations walk ``corporate_entity.parent_entity_id``.
    Unresolved names stay as their own roots -- a missing hierarchy
    match is not a guessed parent.
    """
    post = await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        trees = await fetch_affiliate_forest(conn, post_id)
    return {"post_id": str(post["post_id"]), "trees": trees}


@app.get("/api/posts/{post_id}/voc-evidence")
async def read_post_voc_evidence(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """VOC type label plus extractive excerpts that name classified orgs."""
    post = await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        return await fetch_voc_evidence(conn, post_id, post["voc_type_code"])


@app.post("/api/posts/{post_id}/verify-relations")
async def verify_post_entity_relationships(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Checks this post's `verify_pending` counterparty relationships
    (entity_relationship_classification's LLM output) against external
    web search (relation_verification.py) and persists the outcome, so a
    hallucinated organization/relationship doesn't sit indistinguishable
    from a corroborated one -- see ADR 0005. Gated by post_admin, not
    post_read: a real external-search-call write action, same discipline
    as extract-keymen.
    """
    _require_post_admin(account)
    post = await _load_visible_post(post_id, account, pool)
    client = _relation_verification_client()
    if not client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Relation verification is unavailable: set SEARXNG_BASE_URL",
        )
    async with pool.acquire() as conn:
        verified = await verify_post_relations(
            conn,
            client,
            post_id,
            visible_corporate_entity_ids=account.corporate_entity_ids,
        )
    return {
        "post_id": str(post["post_id"]),
        "verified": [
            {
                "counterparty_entity_name": row.counterparty_entity_name,
                "verification_status_code": row.verification_status_code,
                "verification_evidence_url": row.verification_evidence_url,
                "verification_evidence_post_id": row.verification_evidence_post_id,
            }
            for row in verified
        ],
    }


@app.post("/api/posts/{post_id}/extract-keymen")
async def extract_post_keymen(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Runs Keyman extraction over a post's own title+body and persists the
    result (cataloged_person / person_affiliation / post_person_mention /
    knowledge_graph_edge), then classifies each affiliated organization's
    relationship to the post author's org (post_counterparty_entity).
    Gated by post_admin, not post_read: this is a write action with a
    real LLM-call cost, not a read.
    """
    _require_post_admin(account)
    post = await _load_visible_post(post_id, account, pool)
    keyman_client = _keyman_extraction_client()
    if not keyman_client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Keyman extraction is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
        )
    relationship_client = _entity_relationship_client()
    async with pool.acquire() as conn:
        body_row = await conn.fetchrow("select post_body from source_post where post_id = $1", post_id)
        raw_body = "" if body_row is None else body_row["post_body"]
        # HTML/base64-image content must never reach an LLM prompt raw --
        # tags dilute the model's attention and a base64 payload sent as
        # literal text either blows the token budget or is silently
        # ignored (see lineageweave/post_content_normalization.py).
        post_body = normalize_post_body(raw_body, vision_client=_vision_client()).text
        context_hints = await _load_post_semantic_hints(conn, post_id)
        mentions = await ingest_post_keymen(
            conn,
            keyman_client,
            post_id,
            post["post_title"],
            post_body,
            resolution_client=_organization_name_resolution_client(),
            verification_client=_relation_verification_client(),
            hierarchy_inference_client=_corporate_hierarchy_inference_client(),
            context_hints=context_hints,
            persist_graph=False,
        )
        organization_names = sorted(
            {name for mention in mentions for name in mention.affiliated_organization_names}
        )
        # relationship_client is gated by the same settings check as
        # keyman_client above (both read ORCHESTRATOR_BASE_URL/_API_KEY),
        # so reaching here means it is available too.
        relationships = await ingest_post_entity_relationships(
            conn, relationship_client, post_id, post["post_title"], post_body, organization_names
        )
        async with conn.transaction():
            await persist_edges_for_post(conn, post_id)
    return {
        "post_id": str(post["post_id"]),
        "extracted_count": len(mentions),
        "mentions": [
            {
                "person_name": mention.person_name,
                "person_side_code": mention.person_side_code,
                "affiliated_organization_names": list(mention.affiliated_organization_names),
                "job_title": mention.job_title,
            }
            for mention in mentions
        ],
        "counterparties": [
            {
                "organization_name": relationship.organization_name,
                "relationship_type_code": relationship.relationship_type_code,
            }
            for relationship in relationships
        ],
    }


@app.get("/api/posts/{post_id}/lineage")
async def read_post_lineage(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """The Event Lineage panel's data: this post's directly (thread-)linked
    posts and its indirectly (shared-Keyman/organization) linked posts,
    kept as two distinguishable lists -- not merged into one, since they
    are different claims about *why* two posts are related. ABAC-filtered
    per candidate the same way every other endpoint here is.
    """
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        linked = await find_linked_post_ids(conn, post_id)
        candidate_ids = linked.direct | linked.indirect
        rows = {}
        if candidate_ids:
            fetched = await conn.fetch(
                "select post_id, post_title, visibility_code, corporate_entity_id, "
                "btrim(left(source_post_search_text(post_body), 420)) as post_body_excerpt, "
                "char_length(coalesce(post_body, '')) > 420 as post_body_truncated "
                "from source_post where post_id = any($1::uuid[])",
                list(candidate_ids),
            )
            rows = {str(row["post_id"]): row for row in fetched}

    def _visible_summaries(ids: frozenset[str]) -> list[dict[str, Any]]:
        return [
            {
                "post_id": post_id_,
                "post_title": rows[post_id_]["post_title"],
                "post_body_excerpt": rows[post_id_].get("post_body_excerpt"),
                "post_body_truncated": rows[post_id_].get("post_body_truncated", False),
            }
            for post_id_ in ids
            if post_id_ in rows and _can_see_post(account, rows[post_id_])
        ]

    return {
        "post_id": post_id,
        "direct": _visible_summaries(linked.direct),
        "indirect": _visible_summaries(linked.indirect),
    }


@app.get("/api/posts/{post_id}/evaluation")
async def read_post_evaluation(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Persisted IRT responses for this post (ADR 0003 slice 2)."""
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        rows = await fetch_post_evaluation(conn, post_id)
    return {
        "post_id": post_id,
        "rubric_version": RUBRIC_VERSION,
        "responses": [
            {
                "criterion_code": row.criterion_code,
                "criterion_label": row.criterion_label,
                "response_category": row.response_category,
                "rubric_version": row.rubric_version,
            }
            for row in rows
        ],
    }


@app.post("/api/posts/{post_id}/evaluate")
async def evaluate_post(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """LLM-as-a-Judge a post through fast-mlsirm and persist the IRT row.

    Gated by post_admin: a real LLM-call write, same discipline as
    extract-keymen. Null channel is 503, never a fabricated score.
    """
    _require_post_admin(account)
    post = await _load_visible_post(post_id, account, pool)
    client = _post_evaluation_client()
    if not client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Post evaluation is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
        )
    async with pool.acquire() as conn:
        body_row = await conn.fetchrow("select post_body from source_post where post_id = $1", post_id)
    normalized_body = normalize_post_body(
        "" if body_row is None else body_row["post_body"], vision_client=_vision_client()
    ).text
    async with pool.acquire() as conn:
        rows = await ingest_post_evaluation(
            conn, client, post_id, post["post_title"], normalized_body
        )
    return {
        "post_id": str(post["post_id"]),
        "rubric_version": RUBRIC_VERSION,
        "responses": [
            {
                "criterion_code": row.criterion_code,
                "criterion_label": row.criterion_label,
                "response_category": row.response_category,
                "rubric_version": row.rubric_version,
            }
            for row in rows
        ],
    }


@app.get("/api/reports/compare/{period_code}")
async def compare_period_groupings(
    period_code: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """PU / corp / thread scores for one period on the shared metric."""
    _require_post_read(account)
    try:
        parse_period_code(period_code)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    async with pool.acquire() as conn:
        rows = await fetch_period_comparison(conn, period_code)
    visible: list[dict[str, Any]] = []
    for row in rows:
        members = [member for member in row["members"] if _can_see_post(account, member)]
        if not members:
            continue
        visible.append({**row, "members": [], "post_count": len(members)})
    return {"period_code": period_code, "groupings": visible}


@app.get("/api/reports/{grouping_kind}")
async def list_period_reports(
    grouping_kind: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Available calibrated periods for one grouping kind (FIPC trend)."""
    _require_post_read(account)
    if grouping_kind not in GROUPING_KINDS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown grouping_kind")
    async with pool.acquire() as conn:
        summaries = await list_period_report_summaries(conn, grouping_kind)
    visible: list[dict[str, Any]] = []
    for summary in summaries:
        members = [member for member in summary["members"] if _can_see_post(account, member)]
        if not members:
            continue
        visible.append({**summary, "members": [], "post_count": len(members)})
    return {"grouping_kind": grouping_kind, "periods": visible}


@app.get("/api/reports/{grouping_kind}/{period_code}")
async def read_period_reports(
    grouping_kind: str,
    period_code: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Calibrated IRT scores for one grouping kind and calendar period."""
    _require_post_read(account)
    if grouping_kind not in GROUPING_KINDS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown grouping_kind")
    try:
        parse_period_code(period_code)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    async with pool.acquire() as conn:
        reports = await fetch_period_reports(conn, grouping_kind, period_code)
    visible: list[dict[str, Any]] = []
    for report in reports:
        members = [member for member in report["members"] if _can_see_post(account, member)]
        if not members:
            continue
        leftover_pairs = [
            pair
            for pair in report.get("leftover_pairs", [])
            if _can_see_post(account, pair)
        ]
        visible.append(
            {**report, "members": members, "leftover_pairs": leftover_pairs, "post_count": len(members)}
        )
    return {"grouping_kind": grouping_kind, "period_code": period_code, "reports": visible}


@app.post("/api/reports/{grouping_kind}/{period_code}/rebuild")
async def rebuild_period_report_endpoint(
    grouping_kind: str,
    period_code: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Refit or FIPC-score every group in the period. post_admin only."""
    _require_post_admin(account)
    if grouping_kind not in GROUPING_KINDS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown grouping_kind")
    try:
        parse_period_code(period_code)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    async with pool.acquire() as conn:
        async with conn.transaction():
            reports = await rebuild_period_reports(conn, grouping_kind, period_code)
    return {
        "grouping_kind": grouping_kind,
        "period_code": period_code,
        "group_count": len(reports),
        "default_period": iso_week_period(),
    }


@app.get("/api/posts/{post_id}/summary")
async def read_post_summary(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """A Korean summary, key events, and R&R for the popup.

    Returns a persisted row when one exists so a seeded demo stack is
    not empty without a live LLM. Otherwise derives through the
    orchestrator and stores the result. Missing both is 503 -- never a
    fabricated summary.
    """
    post = await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        body_row = await conn.fetchrow(
            "select post_body from source_post where post_id = $1", post_id
        )
        try:
            raw_body = require_summary_source_body(
                None if body_row is None else body_row["post_body"]
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
        stored = await fetch_persisted_summary(conn, post_id)
        if stored is not None:
            return stored
        client = _post_summary_client()
        if not client.available:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Post summary is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
            )
        vision_client = _vision_client()
        normalized = normalize_post_body(raw_body, vision_client=vision_client)
        settings = load_settings()
        embedding_client = _embedding_client()
        if vision_client.available or embedding_client.available:
            await persist_post_content(
                conn,
                post_id,
                raw_body,
                vision_client=vision_client,
                embedding_client=embedding_client,
                embedding_model_code=settings.embedding_model or None,
                normalized_result=normalized,
            )
        normalized_body = normalized.text
        context_hints = await _load_post_semantic_hints(conn, post_id)
        summarize_with_hints = getattr(client, "summarize_with_hints", None)
        try:
            if callable(summarize_with_hints):
                summary = await asyncio.to_thread(
                    summarize_with_hints, post["post_title"], normalized_body, context_hints
                )
            else:
                summary = await asyncio.to_thread(client.summarize, post["post_title"], normalized_body)
        except (HttpClientError, KeyError, OSError, TypeError, ValueError) as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Post summary is unavailable: contextual-orchestrator returned no complete evidence object",
            ) from exc
        return await persist_post_summary(
            conn,
            post_id,
            summary,
            post_body=normalized_body,
            hierarchy_inference_client=_corporate_hierarchy_inference_client(),
            verification_client=_relation_verification_client(),
        )


@app.get("/api/posts/{post_id}/five-w1h")
async def read_post_five_w1h(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Return an evidence-only 5W1H projection for an authorized post."""
    post = await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        return await load_five_w1h_slots(
            conn,
            post_id,
            post["created_at"],
            lambda row: _can_see_post(account, row),
        )


class ChatRequest(BaseModel):
    """JSON body for ``POST /api/posts/{post_id}/chat``."""

    question: str


class GlobalAskRequest(BaseModel):
    """JSON body for the buyer's source-grounded Global Ask Agent."""

    question: str


@app.get("/api/posts/{post_id}/chat")
async def read_post_chat(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Stored Ask exchanges for this post.

    Seeded fixture answers (and any later live persist) so the popup is
    not an empty Ask box when the orchestrator is off. Missing rows are
    an empty list, not a fabricated transcript.
    """
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        exchanges = await fetch_persisted_chats(conn, post_id)
    return {"post_id": post_id, "exchanges": exchanges}


@app.post("/api/posts/{post_id}/chat")
async def chat_about_post(
    post_id: str,
    request: ChatRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """In-popup chat: answers `request.question` using this post's own
    content plus its Event-Lineage-linked posts (direct and Knowledge-
    Graph-indirect) as context, and returns which source post(s) the
    answer drew from -- the sliding evidence panel's citation data.

    A persisted (seeded or previously live) row is returned first so
    Ask works on the demo stack without an orchestrator. Live
    reason-and-cite still runs only when no stored match exists and
    the orchestrator is configured -- never a fabricated reply.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "question is required")
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        stored = await fetch_persisted_chat(conn, post_id, question)
        if stored is not None:
            source_ids = [post_id]
            source_ids.extend(cid for cid in stored["cited_post_ids"] if cid != post_id)
            return {
                "post_id": post_id,
                "answer_text": stored["answer_text"],
                "cited_post_ids": stored["cited_post_ids"],
                "cited_posts": stored["cited_posts"],
                "source_post_ids": source_ids,
            }
        client = _post_chat_client()
        if not client.available:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Post chat is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
            )
        sources = await gather_chat_sources(
            conn, post_id, lambda row: _can_see_post(account, row), vision_client=_vision_client()
        )
    try:
        answer = await asyncio.to_thread(client.answer, question, sources)
    except (HttpClientError, KeyError, OSError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Post chat is unavailable: contextual-orchestrator returned no complete evidence object",
        ) from exc
    cited_ids = list(answer.cited_post_ids)
    async with pool.acquire() as conn:
        await persist_post_chat(conn, post_id, question, answer.answer_text, cited_ids)
    return {
        "post_id": post_id,
        "answer_text": answer.answer_text,
        "cited_post_ids": cited_ids,
        "cited_posts": cited_post_summaries(sources, cited_ids),
        "source_post_ids": [source.post_id for source in sources],
    }


@app.post("/api/ask")
async def ask_agent(
    request: GlobalAskRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Answer a buyer question from authorized post and graph evidence."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "question is required")
    _require_post_read(account)
    client = _post_chat_client()
    if not client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ask Agent is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
        )
    async with pool.acquire() as conn:
        sources = await gather_global_chat_sources(
            conn,
            lambda row: _can_see_post(account, row),
            account.corporate_entity_ids,
            question=question,
        )
    if not sources:
        return {
            "answer_text": "",
            "cited_post_ids": [],
            "cited_posts": [],
            "source_post_ids": [],
            "cited_post_evidence": [],
            "next_action": "No authorized source posts are available for this question.",
        }
    try:
        answer = await asyncio.to_thread(client.answer, question, sources)
    except (HttpClientError, KeyError, OSError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Ask Agent is unavailable: {exc}",
        ) from exc
    cited_ids = list(answer.cited_post_ids)
    return {
        "answer_text": answer.answer_text,
        "cited_post_ids": cited_ids,
        "cited_posts": cited_post_summaries(sources, cited_ids),
        "cited_post_evidence": cited_post_evidence(sources, cited_ids),
        "source_post_ids": [source.post_id for source in sources],
    }


@app.get("/api/posts/{post_id}/tickets")
async def read_post_tickets(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """List issue tickets on one visible post. Read-only, so post_read
    is enough -- same gate as every other post-scoped GET here.
    """
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        tickets = await list_tickets_for_post(conn, post_id)
    return {"post_id": post_id, "tickets": tickets}


class CreateTicketRequest(BaseModel):
    """JSON body for ``POST /api/posts/{post_id}/tickets``."""

    ticket_title: str
    ticket_status_code: str
    assigned_account_id: str | None = None
    # Manual calendar/to-do date, e.g. YYYY-MM-DD. Set automatically instead
    # by POST /api/posts/{post_id}/derive-commitment when the LLM should
    # decide it.
    due_date: str | None = None


@app.post("/api/posts/{post_id}/tickets", status_code=status.HTTP_201_CREATED)
async def create_post_ticket(
    post_id: str,
    request: CreateTicketRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
    valkey: redis.Redis = Depends(get_valkey),
) -> dict[str, Any]:
    """Create an issue ticket on a visible post. post_admin-gated: opening
    a ticket is a write action, same discipline as extract-keymen.
    """
    _require_post_admin(account)
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        try:
            ticket = await create_ticket(
                conn,
                post_id,
                request.ticket_title,
                request.ticket_status_code,
                request.assigned_account_id,
                due_date=request.due_date,
            )
        except asyncpg.ForeignKeyViolationError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"ticket_status_code {request.ticket_status_code!r} is not a valid ticket_status lookup code",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"due_date {request.due_date!r} is not a valid YYYY-MM-DD date",
            ) from exc
    await publish_activity_event(
        valkey,
        post_id,
        "ticket_created",
        account.user_account_id,
        ticket_created_summary(request.ticket_title),
    )
    return ticket


class UpdateTicketRequest(BaseModel):
    """JSON body for ``PATCH /api/tickets/{issue_ticket_id}``.

    ``assigned_account_id`` left unset means "don't touch it";
    ``clear_assignment=True`` explicitly unassigns. Both are distinct,
    expressible outcomes a partial-update endpoint needs.
    """

    ticket_status_code: str | None = None
    assigned_account_id: str | None = None
    clear_assignment: bool = False


@app.patch("/api/tickets/{issue_ticket_id}")
async def patch_ticket(
    issue_ticket_id: str,
    request: UpdateTicketRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
    valkey: redis.Redis = Depends(get_valkey),
) -> dict[str, Any]:
    """Update a ticket's status and/or assignee. post_admin-gated. The
    ABAC check runs against the ticket's OWNING post, resolved first --
    a ticket has no visibility_code of its own, it inherits its post's.
    """
    _require_post_admin(account)
    async with pool.acquire() as conn:
        post_id = await fetch_ticket_post_id(conn, issue_ticket_id)
        if post_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "ticket not found")
    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        try:
            ticket = await update_ticket(
                conn,
                issue_ticket_id,
                request.ticket_status_code,
                request.assigned_account_id,
                request.clear_assignment,
            )
        except asyncpg.ForeignKeyViolationError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"ticket_status_code {request.ticket_status_code!r} is not a valid ticket_status lookup code",
            ) from exc
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ticket not found")
    if request.ticket_status_code is not None:
        await publish_activity_event(
            valkey,
            post_id,
            "ticket_status_changed",
            account.user_account_id,
            ticket_status_changed_summary(
                ticket.get("ticket_status_label") or request.ticket_status_code
            ),
        )
    return ticket


@app.get("/api/posts/{post_id}/activity")
async def read_post_activity(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
    valkey: redis.Redis = Depends(get_valkey),
) -> dict[str, Any]:
    """The post's activity feed, read straight off its Valkey stream
    (``XREVRANGE``) -- newest first. Read-only, so post_read is enough.
    """
    await _load_visible_post(post_id, account, pool)
    events = await read_activity_events(valkey, post_id)
    return {"post_id": post_id, "events": events}


@app.post("/api/posts/{post_id}/derive-commitment")
async def derive_post_commitment(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
    valkey: redis.Redis = Depends(get_valkey),
) -> dict[str, Any]:
    """LLM-derive a customer commitment (if any) from a post's own text,
    and -- when found -- register it as an issue_ticket with a due_date,
    which is what makes it show up on GET /api/calendar. post_admin-gated:
    a real LLM-call write action, same discipline as extract-keymen.
    `has_commitment: false` is a normal 200 response, not an error --
    most posts genuinely have no commitment in them.
    """
    _require_post_admin(account)
    post = await _load_visible_post(post_id, account, pool)
    client = _commitment_extraction_client()
    if not client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Commitment derivation is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
        )
    async with pool.acquire() as conn:
        body_row = await conn.fetchrow("select post_body from source_post where post_id = $1", post_id)
    normalized_body = normalize_post_body(body_row["post_body"], vision_client=_vision_client()).text
    # TimeML/TempEval document creation time, not wall-clock now: "by next
    # Friday" in a January post must resolve to that January, not to the
    # Friday after the operator clicked Derive.
    reference_date = post["created_at"].date().isoformat()
    commitment = client.extract(post["post_title"], normalized_body, reference_date)
    if not commitment.has_commitment:
        return {"post_id": str(post["post_id"]), "has_commitment": False, "ticket": None}
    async with pool.acquire() as conn:
        try:
            ticket = await upsert_commitment_ticket(
                conn,
                post_id,
                commitment.commitment_summary,
                commitment.due_date,
                commitment.commitment_summary,
            )
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"due_date {commitment.due_date!r} is not a valid YYYY-MM-DD date",
            ) from exc
    await publish_activity_event(
        valkey,
        post_id,
        "commitment_derived",
        account.user_account_id,
        f"Commitment derived: {commitment.commitment_summary}",
    )
    return {"post_id": str(post["post_id"]), "has_commitment": True, "ticket": ticket}


@app.get("/api/analysis-runs")
async def list_analysis_runs(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Authorized analysis-run list: aggregates and labels only.

    Hidden scopes 404 at the item path and never appear here. The
    payload has no source SQL, DSN, raw record, or provider body.
    """
    _require_post_read(account)
    async with pool.acquire() as conn:
        runs = await fetch_visible_analysis_runs(
            conn,
            account.user_account_id,
            list(account.corporate_entity_ids),
        )
    return {"analysis_runs": runs}


class CreateAnalysisRunRequest(BaseModel):
    """JSON body for ``POST /api/analysis-runs``.

    Omitting ``corporate_entity_id`` uses the account's sole affiliation.
    Only ``analysis_run_lineage`` is accepted. Reconstruction and TEPP
    execution stay later slices; this write records Pending lineage only.
    """

    run_kind_code: str = "analysis_run_lineage"
    scope_kind_code: str = "analysis_scope_corporate_entity"
    corporate_entity_id: str | None = None
    knowledge_cutoff: datetime | None = None
    idempotency_key: str


@app.post("/api/analysis-runs", status_code=status.HTTP_201_CREATED)
async def create_analysis_run(
    request: CreateAnalysisRunRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Record a Pending lineage run on an authorized cutoff capture.

    post_read is enough: the caller requests a run of a corp they
    already walk. TEPP and period-report kinds are 422 so this path
    cannot invent a measurement. Hidden scopes 404. A matching
    idempotent retry returns the same run.
    """
    _require_post_read(account)
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                created = await create_pending_analysis_run(
                    conn,
                    account_id=account.user_account_id,
                    affiliated_entity_ids=list(account.corporate_entity_ids),
                    run_kind_code=request.run_kind_code,
                    scope_kind_code=request.scope_kind_code,
                    corporate_entity_id=request.corporate_entity_id,
                    knowledge_cutoff=request.knowledge_cutoff,
                    idempotency_key=request.idempotency_key,
                )
            except AnalysisRunCreateError as exc:
                raise HTTPException(exc.status_code, exc.detail) from exc
    return created


@app.post("/api/analysis-runs/{analysis_run_id}/start")
async def start_analysis_run(
    analysis_run_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
    valkey: redis.Redis = Depends(get_valkey),
) -> dict[str, Any]:
    """Enqueue start work, then deliver ThreadWeave or TEPP.

    post_read is enough. Hidden runs 404. Period-report is 422 so this
    path cannot invent a calibrated score. TEPP goes through
    ``tepp_client`` and stays Failed when the transport is missing or
    the envelope is not persistable. A Succeeded lineage retry returns
    the stored tree. A Running restart with an undelivered outbox
    finishes that work. A Running restart without pending work is 409.
    The outbox commits before reconstruct/TEPP so a crash leaves a
    durable work item (ADR 0023).
    """
    _require_post_read(account)
    settings = load_settings()
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                queued = await enqueue_pending_analysis_run(
                    conn,
                    analysis_run_id=analysis_run_id,
                    account_id=account.user_account_id,
                    affiliated_entity_ids=list(account.corporate_entity_ids),
                )
            except AnalysisRunStartError as exc:
                raise HTTPException(exc.status_code, exc.detail) from exc
    if queued.get("status_code") == "analysis_status_succeeded":
        return queued
    request_digest = queued.pop("outbox_request_sha256", None)
    stream_id = None
    if request_digest:
        stream_id = await publish_outbox_event(
            valkey,
            analysis_run_id=analysis_run_id,
            work_kind_code=str(queued.get("run_kind_code") or ""),
            request_sha256=request_digest,
        )
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                started = await deliver_queued_analysis_run(
                    conn,
                    analysis_run_id=analysis_run_id,
                    account_id=account.user_account_id,
                    affiliated_entity_ids=list(account.corporate_entity_ids),
                    tepp_client=configured_tepp_client(
                        settings.tepp_transport_url,
                        settings.tepp_api_key,
                    ),
                    valkey_stream_entry_id=stream_id,
                )
            except AnalysisRunStartError as exc:
                raise HTTPException(exc.status_code, exc.detail) from exc
    return started


@app.get("/api/analysis-runs/{analysis_run_id}")
async def read_analysis_run(
    analysis_run_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """One authorized analysis-run projection, or 404 when hidden.

    Detail adds the labeled status history. Hidden runs never leak events.
    """
    _require_post_read(account)
    try:
        UUID(analysis_run_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "analysis run not found") from None
    async with pool.acquire() as conn:
        run = await fetch_visible_analysis_run(
            conn,
            analysis_run_id,
            account.user_account_id,
            list(account.corporate_entity_ids),
        )
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "analysis run not found")
    return run


@app.get("/api/calendar")
async def read_calendar(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Return independent CalDAV events alongside authorized commitments.

    An unavailable optional CalDAV source never hides the internal to-do
    projection and never creates a synthetic event.
    """
    _require_post_read(account)
    caldav = build_caldav_client(load_settings().caldav_base_url)
    events = []
    caldav_available = caldav.available
    caldav_next_action = None
    if caldav.available:
        try:
            events = [asdict(event) for event in caldav.list_events()]
        except (HttpClientError, OSError, ValueError):
            caldav_available = False
            caldav_next_action = CALDAV_UNAVAILABLE_NEXT_ACTION
    else:
        caldav_next_action = CALDAV_UNAVAILABLE_NEXT_ACTION
    async with pool.acquire() as conn:
        commitments = await fetch_upcoming_commitments(conn)
    visible = [c for c in commitments if _can_see_post(account, c)]
    for c in visible:
        del c["visibility_code"], c["corporate_entity_id"]
    return {
        "events": events,
        "commitments": visible,
        "calendar_sources": {
            "caldav_available": caldav_available,
            "caldav_next_action": caldav_next_action,
        },
    }


@app.get("/api/rankings")
async def read_rankings(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """RankWeave fusion of ABAC-visible posts (ADR 0024).

    Hidden posts are omitted from every channel. Never invents a fused
    score or a theta. Fail-closed when RankWeave is disabled or the
    library is missing.
    """
    _require_post_read(account)
    async with pool.acquire() as conn:
        posts = await load_visible_ranking_posts(
            conn, lambda row: _can_see_post(account, row)
        )
    return _rankweave_client().as_api_payload(
        posts, can_see_post=lambda _row: True
    )
