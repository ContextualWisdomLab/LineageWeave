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
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import Any, Literal
from uuid import UUID

import asyncpg
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Path, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lineageweave.claim_verification import (
    NullClaimVerificationClient,
    SearxngOrchestratedClaimVerificationClient,
)

from backend.app.activity_stream import (
    create_valkey_client,
    get_valkey,
    publish_activity_event,
    read_activity_events,
    ticket_created_summary,
    ticket_status_changed_summary,
)
from backend.app.affiliate_tree_ingestion import (
    fetch_affiliate_forest,
    fetch_voc_evidence,
)
from lineageweave.similar_voc import ContextualOrchestratorSimilarVocAnalysisClient
from lineageweave.naruon_calendar_workspace import (
    build_workspace_naruon_client,
    default_calendar_window,
    load_observed_calendar_events,
)
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
from backend.app.auth import CurrentAccount, get_current_account
from backend.app.config import load_settings
from backend.app.customer_hint_ingestion import resolve_customer_hint
from backend.app.db import create_pool, get_pool
from backend.app.demo_scope import (
    fetch_demo_corporate_entity_ids,
    has_real_source_context,
)
from backend.app.entity_relationship_ingestion import (
    fetch_post_counterparties,
    fetch_relationship_network,
    ingest_post_entity_relationships,
)
from backend.app.five_w1h_ingestion import load_five_w1h_slots
from backend.app.global_ask_queue import (
    run_global_ask_worker,
)
from backend.app.global_ask_service import read_global_ask_job, submit_global_ask
from backend.app.issue_ticket_ingestion import (
    create_ticket,
    fetch_ticket_post_id,
    fetch_upcoming_commitments,
    list_tickets_for_post,
    update_ticket,
    upsert_commitment_ticket,
)
from backend.app.operations_dashboard import fetch_operations_dashboard
from backend.app.keyman_ingestion import ingest_post_keymen
from backend.app.knowledge_graph import (
    corporate_entity_exists,
    fetch_person_role_history,
    fetch_post_keymen,
    labels_for_codes,
    persist_edges_for_post,
    person_exists,
    related_for_entity,
    related_for_person,
    related_for_team,
    team_exists,
    visible_affiliation_post_ids,
    visible_mention_post_ids,
    visible_team_mention_post_ids,
)
from backend.app.lineage_ingestion import (
    ChannelWeightsNotEstimated,
    interval_relations_for_post,
    lineage_graphs_for_posts,
    rebuild_lineage_from_pool,
    visible_lineage_graph,
)
from backend.app.ontology_neighborhood_ingestion import (
    neighborhood_error_detail,
    neighborhood_error_http_status,
    neighborhood_to_payload,
    parse_allowed_property_query,
    visible_ontology_neighborhood,
)
from backend.app.iopsy_ontology_api import (
    construct_catalog_payload,
    worker_function_profile_payload,
)
from backend.app.post_chat_ingestion import (
    fetch_persisted_chat,
    fetch_persisted_chats,
    find_linked_post_ids,
    gather_chat_sources,
    persist_post_chat,
)
from backend.app.post_content_queue import (
    ensure_post_content_job,
    post_content_api_status,
    post_content_is_complete,
    publish_post_content_event,
)
from backend.app.occupational_construct_ingestion import (
    load_occupational_construct_assertions,
)
from backend.app.occupational_construct_search import (
    OccupationalConstructSearchError,
    occupational_construct_search_error_detail,
    occupational_construct_search_http_status,
    search_page_to_payload,
    search_visible_occupational_constructs,
)
from backend.app.post_content_worker import run_post_content_worker
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL, source_post_visible
from backend.app.post_evaluation_ingestion import (
    fetch_post_evaluation,
    ingest_post_evaluation,
)
from backend.app.occupation_rating_ingestion import (
    fetch_occupation_rating_sources,
    fetch_occupation_ratings,
    fetch_rating_source_occupations,
)
from backend.app.project_history import (
    ProjectHistoryNotFound,
    ProjectHistoryRequestError,
    fetch_project_history_projection,
)
from backend.app.post_summary_ingestion import (
    fetch_persisted_summary,
    persist_post_summary,
    require_summary_source_body,
)
from backend.app.ranking_ingestion import load_visible_ranking_posts
from backend.app.relation_verification_ingestion import verify_post_relations_from_pool
from backend.app.report_ingestion import (
    GROUPING_KINDS,
    fetch_period_comparison,
    fetch_period_reports,
    iso_week_period,
    list_period_report_summaries,
    parse_period_code,
    rebuild_period_reports,
)
from backend.app.source_post_revision import fetch_known_at_revision, parse_as_of_clock
from backend.app.source_post_voice_ingestion import (
    PrimaryVoiceAssignmentError,
    persist_additional_voice_assignment,
)
from lineageweave.adjudication_client import (
    AdjudicationClientError,
    ContextualOrchestratorAdjudicationClient,
    NullAdjudicationClient,
)
from lineageweave.commitment_extraction import (
    ContextualOrchestratorCommitmentExtractionClient,
    NullCommitmentExtractionClient,
)
from lineageweave.corporate_hierarchy_inference import (
    ContextualOrchestratorHierarchyInferenceClient,
    NullCorporateHierarchyInferenceClient,
)
from lineageweave.customer_hint_resolution import (
    ContextualOrchestratorCustomerHintResolutionClient,
    NullCustomerHintResolutionClient,
)
from lineageweave.embedding_client import orchestrator_embedding_client
from lineageweave.entity_relationship_classification import (
    ContextualOrchestratorEntityRelationshipClient,
    NullEntityRelationshipClient,
)
from lineageweave.http_client import HttpClientError
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.keyman_extraction import (
    COUNTERPARTY,
    ContextualOrchestratorKeymanExtractionClient,
    NullKeymanExtractionClient,
)
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.observability import (
    configure_telemetry,
    record_server_failure,
    shutdown_telemetry,
    traced,
)
from lineageweave.ontology import LW
from lineageweave.ontology_neighborhood import (
    DEFAULT_MAXIMUM_DEPTH,
    DEFAULT_MAXIMUM_EDGES,
    DEFAULT_MAXIMUM_NODES,
    HARD_MAXIMUM_DEPTH,
    HARD_MAXIMUM_EDGES,
    HARD_MAXIMUM_NODES,
    OntologyNeighborhoodError,
)
from lineageweave.organization_name_resolution import (
    ContextualOrchestratorOrganizationNameResolutionClient,
    NullOrganizationNameResolutionClient,
)
from lineageweave.post_chat import (
    ContextualOrchestratorPostChatClient,
    NullPostChatClient,
    cited_post_summaries,
)
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_evaluation import (
    RUBRIC_VERSION,
    ContextualOrchestratorPostEvaluationClient,
    NullPostEvaluationClient,
)
from lineageweave.post_structure import (
    ContextualOrchestratorPostStructureClient,
    NullPostStructureClient,
)
from lineageweave.post_summary import (
    ContextualOrchestratorPostSummaryClient,
    NullPostSummaryClient,
)
from lineageweave.rankweave_client import build_rankweave_client
from lineageweave.relation_verification import (
    NullRelationVerificationClient,
    SearxngRelationVerificationClient,
)
from lineageweave.semantic_hints import customer_hint_trust, format_semantic_hints
from lineageweave.semantic_query import (
    ContextualOrchestratorSemanticQueryClient,
    NullSemanticQueryClient,
)

_POST_READ = "post_read"
_POST_ADMIN = "post_admin"
_SIMILAR_VOC_PAGE_SIZE = 8
_SIMILAR_VOC_REQUEST_TIMEOUT_SECONDS = 180.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open one asyncpg pool and one Valkey client for the process, and
    close both on shutdown."""
    configure_telemetry("lineageweave")
    pool = None
    valkey = None
    analysis_worker = None
    content_worker = None
    global_ask_worker = None
    try:
        settings = load_settings()
        pool = await create_pool(settings.database_url)
        app.state.pool = pool
        valkey = create_valkey_client(settings.valkey_url)
        app.state.valkey = valkey
        analysis_worker = asyncio.create_task(
            run_analysis_run_worker(
                valkey,
                pool,
                database_url=settings.database_url,
                tepp_client=configured_tepp_client(
                    settings.tepp_transport_url,
                    settings.tepp_api_key,
                ),
                adjudication_client=_adjudication_client(),
            )
        )
        app.state.analysis_run_worker = analysis_worker
        content_worker = asyncio.create_task(
            run_post_content_worker(
                valkey,
                pool,
                vision_factory=_vision_client,
                embedding_factory=_embedding_client,
                structure_factory=_post_structure_client,
            )
        )
        app.state.post_content_worker = content_worker
        # Late-bound lambda so tests that monkeypatch _post_chat_client reach
        # the worker too (the name resolves in module globals at call time).
        # Only this worker gets the long answer timeout; the per-post chat
        # endpoint keeps the client's interactive default.
        global_ask_worker = asyncio.create_task(
            run_global_ask_worker(
                valkey,
                pool,
                chat_factory=lambda: _post_chat_client(
                    timeout=load_settings().orchestrator_answer_timeout_seconds
                ),
                embedding_factory=_embedding_client,
                semantic_query_factory=_semantic_query_client,
                claim_verification_factory=_claim_verification_client_factory,
            )
        )
        app.state.global_ask_worker = global_ask_worker
        yield
    finally:
        workers = tuple(
            worker
            for worker in (analysis_worker, content_worker, global_ask_worker)
            if worker is not None
        )
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
        try:
            if pool is not None:
                await pool.close()
        finally:
            try:
                if valkey is not None:
                    await valkey.aclose()
            finally:
                shutdown_telemetry()


logger = logging.getLogger(__name__)

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


def _claim_verification_client():
    """Return the public-evidence verifier, or its unavailable null channel."""

    settings = load_settings()
    if not (
        settings.searxng_base_url
        and settings.orchestrator_base_url
        and settings.orchestrator_api_key
    ):
        return NullClaimVerificationClient()
    return SearxngOrchestratedClaimVerificationClient(
        settings.searxng_base_url,
        settings.orchestrator_base_url,
        settings.orchestrator_api_key,
    )


def _claim_verification_client_factory():
    """Resolve the verifier late so runtime overrides reach the worker."""
    return _claim_verification_client()


def _organization_name_resolution_client():
    """Live orchestrator client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullOrganizationNameResolutionClient()
    return ContextualOrchestratorOrganizationNameResolutionClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _customer_hint_resolution_client():
    """Live orchestrator client when configured; otherwise the unavailable null.

    A longer timeout than the other channels' default 30s: this prompt
    carries up to five posts' excerpts, not one short mention -- a real
    resolve call measured 137.6s live end-to-end (90s was not enough
    margin and made every real hint 503; 200s gives real headroom).
    """
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullCustomerHintResolutionClient()
    return ContextualOrchestratorCustomerHintResolutionClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key, timeout=200.0
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


def _adjudication_client():
    """Live orchestrator client when configured; otherwise the unavailable null.

    The llm channel is the only one that reasons about content instead
    of approximating it (ADR 0064). Its fusion weight -- like every
    channel's -- is a fast-mlsirm estimate (ADR 0200): with this client
    available, a four-channel run uses the persisted
    `channel_set_with_llm` estimate and fails closed until one exists.
    """
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullAdjudicationClient()
    return ContextualOrchestratorAdjudicationClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _post_structure_client():
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullPostStructureClient()
    return ContextualOrchestratorPostStructureClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _post_chat_client(timeout: float | None = None):
    """Live orchestrator client when configured; otherwise the unavailable null.

    ``timeout`` overrides the client's socket timeout. Only the Ask worker
    passes the long answer timeout — the synchronous per-post chat endpoint
    keeps the client default so an interactive request never hangs a reader
    for the worker's full budget.
    """
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullPostChatClient()
    kwargs = {} if timeout is None else {"timeout": timeout}
    return ContextualOrchestratorPostChatClient(
        base_url=settings.orchestrator_base_url,
        api_key=settings.orchestrator_api_key,
        **kwargs,
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

    Same contextual-orchestrator gateway as every other channel. The model is
    intentionally omitted so contextual-orchestrator selects the registered
    vision-capable provider agent; LineageWeave never selects ``VISION_MODEL``.
    """
    settings = load_settings()
    return orchestrator_vision_client(
        settings.orchestrator_base_url,
        settings.orchestrator_api_key,
    )


def _embedding_client():
    """Build the orchestrator embedding client, or an unavailable channel."""
    settings = load_settings()
    return orchestrator_embedding_client(
        settings.orchestrator_base_url,
        settings.orchestrator_api_key,
    )


def _semantic_query_client():
    """Build the orchestrator query rewriter, or an unavailable channel."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullSemanticQueryClient()
    return ContextualOrchestratorSemanticQueryClient(
        settings.orchestrator_base_url, settings.orchestrator_api_key
    )


def _post_evaluation_client():
    """Live judge client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullPostEvaluationClient()
    return ContextualOrchestratorPostEvaluationClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


def _similar_voc_client():
    """Live semantic-pair client, or ``None`` when inference is unavailable."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return None
    return ContextualOrchestratorSimilarVocAnalysisClient(
        base_url=settings.orchestrator_base_url,
        api_key=settings.orchestrator_api_key,
        timeout=_SIMILAR_VOC_REQUEST_TIMEOUT_SECONDS,
    )


def _rankweave_client():
    """In-process RankWeave unless RANKWEAVE_DISABLED=1 (ADR 0024)."""
    return build_rankweave_client(disabled=load_settings().rankweave_disabled)


def _can_see_post(account: CurrentAccount, post: asyncpg.Record) -> bool:
    """ABAC: public rows are visible; private rows require the bound local scope."""
    return source_post_visible(
        post, account.corporate_entity_ids, account.process_unit_ids
    )


def _is_synthetic_demo_member(member: dict[str, Any], demo_entity_ids: set[str]) -> bool:
    """Identify one pure seed row without hiding real rows sharing its entity."""
    return bool(demo_entity_ids) and member["corporate_entity_id"] in demo_entity_ids and not bool(
        member.get("has_real_source_context", False)
    )


def _serialize_post(post: asyncpg.Record, labels: dict[str, str] | None = None) -> dict[str, Any]:
    """Turn a ``source_post`` row into the public JSON shape."""
    resolved = labels or {}
    voc = post["voc_type_code"]
    visibility = post["visibility_code"]
    project_evidence = post.get("project_evidence") or []
    if isinstance(project_evidence, str):
        project_evidence = json.loads(project_evidence)
    voice_types = post.get("voice_types") or []
    if isinstance(voice_types, str):
        voice_types = json.loads(voice_types)
    return {
        "post_id": str(post["post_id"]),
        "post_title": post["post_title"],
        "voc_type_code": voc,
        "voc_type_label": resolved.get(voc, voc),
        "voice_types": voice_types,
        "visibility_code": visibility,
        "visibility_label": resolved.get(visibility, visibility),
        "source_stage_code": post.get("source_stage_code"),
        "source_detail_state_code": post.get("source_detail_state_code"),
        "source_draft_code": post.get("source_draft_code"),
        "source_deleted_flag": post.get("source_deleted_flag"),
        "publication_state_code": _publication_state_code(post),
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


def _publication_state_code(post: asyncpg.Record) -> str:
    """Expose raw lifecycle evidence without guessing its source semantics."""
    if str(post.get("source_deleted_flag") or "").strip():
        return "source_deletion_marker"
    if str(post.get("source_draft_code") or "").strip():
        return "source_draft_marker"
    return "publication_state_unknown"


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


async def _load_post_voice_types(
    conn: asyncpg.Connection,
    post_id: str,
    effective_cutoff: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return qualified Voice-of-X associations without exposing assertion ids."""
    rows = await conn.fetch(
        """
        select voice.voice_type_code, lookup.lookup_label, voice.is_primary,
               voice.truth_status_code,
               voice.provenance_assertion_id is not null as evidence_available
          from source_post_voice voice
          join common_lookup_value lookup
            on lookup.lookup_category = 'voc_type'
           and lookup.lookup_code = voice.voice_type_code
         where voice.post_id = $1
           and (($2::timestamptz is null and voice.effective_to is null)
                or ($2::timestamptz is not null
                    and voice.effective_from <= $2
                    and (voice.effective_to is null or $2 < voice.effective_to)))
         order by voice.is_primary desc, lookup.display_order, voice.voice_type_code
        """,
        post_id,
        effective_cutoff,
    )
    return [
        {
            "code": row["voice_type_code"],
            "label": row["lookup_label"],
            "is_primary": row["is_primary"],
            "truth_status_code": row["truth_status_code"],
            "evidence_available": row["evidence_available"],
        }
        for row in rows
    ]


async def _post_filter_options(
    conn: asyncpg.Connection,
    corporate_entity_ids: frozenset[str],
    process_unit_ids: frozenset[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return every authorized filter value, not only values on the current page."""
    options_sql = f"""
        select distinct option.lookup_category, option.code,
               coalesce(lookup.lookup_label, option.code) as label,
               coalesce(lookup.display_order, 2147483647) as display_order
          from source_post post
          left join source_post_voice voice
            on voice.post_id = post.post_id and voice.effective_to is null
         cross join lateral (
               values ('post_visibility', post.visibility_code),
                      ('voc_type', coalesce(voice.voice_type_code, post.voc_type_code))
         ) as option(lookup_category, code)
          left join common_lookup_value lookup
            on lookup.lookup_category = option.lookup_category
           and lookup.lookup_code = option.code
         where (post.visibility_code = 'public'
            or (post.corporate_entity_id::text = any($1::text[])
                and (cardinality($2::text[]) = 0
                     or post.process_unit_id::text = any($2::text[]))))
           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
         order by option.lookup_category, display_order, option.code
    """
    option_rows = await conn.fetch(
        options_sql, list(corporate_entity_ids), list(process_unit_ids)
    )
    return (
        [
            {"code": row["code"], "label": row["label"]}
            for row in option_rows
            if row["lookup_category"] == "voc_type"
        ],
        [
            {"code": row["code"], "label": row["label"]}
            for row in option_rows
            if row["lookup_category"] == "post_visibility"
        ],
    )


@app.get("/api/settings", response_model=dict)
async def read_tenant_settings(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT brand_name FROM tenant_settings WHERE id = 1")
    if not row:
        return {"brandName": "LineageWeave"}
    return {"brandName": row["brand_name"]}

@app.patch("/api/settings", response_model=dict)
async def update_tenant_settings(
    payload: dict,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
):
    _require_post_admin(account)
    brand_name = payload.get("brandName", "LineageWeave")
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO tenant_settings (id, brand_name) VALUES (1, $1) "
            "ON CONFLICT (id) DO UPDATE SET brand_name = $1",
            brand_name
        )
    return {"brandName": brand_name}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/me")
async def read_me(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
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
        "preferred_locale": account.preferred_locale,
        "permission_codes": sorted(account.permission_codes),
        "corporate_entities": entities,
    }


@app.get("/api/dashboard")
async def operations_dashboard(
    period_start: date | None = Query(None),
    period_end: date | None = Query(None),
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    _require_post_read(account)
    async with pool.acquire() as conn:
        try:
            return await fetch_operations_dashboard(
                conn,
                account.corporate_entity_ids,
                account.process_unit_ids,
                period_start,
                period_end,
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


class LocalePreferenceRequest(BaseModel):
    preferred_locale: Literal["en", "ko", "zh", "ja", "vi"]


class CustomerHintResolveRequest(BaseModel):
    hint_code: str


@app.patch("/api/me/preferences")
async def update_me_preferences(
    preference: LocalePreferenceRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, str]:
    async with pool.acquire() as conn:
        await conn.execute(
            "update user_account set preferred_locale = $1 where user_account_id = $2",
            preference.preferred_locale,
            account.user_account_id,
        )
    return {"preferred_locale": preference.preferred_locale}


@app.get("/api/customer-master")
async def read_customer_master(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    _require_post_read(account)
    if not account.corporate_entity_ids:
        return {
            "corporate_entities": [],
            "keymen": [],
            "source_customer_hints": [],
            "source_author_hints": [],
            "relationship_network": [],
        }

    async with pool.acquire() as conn:
        source_customer_rows = await conn.fetch(
            f"""
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
                   and (visibility_code = 'public' or (
                        corporate_entity_id = any($1::uuid[])
                        and (cardinality($2::uuid[]) = 0
                             or process_unit_id = any($2::uuid[]))))
                   and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}
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
            ), top_groups as materialized (
                select *
                  from groups
                 order by post_count desc, customer_code, customer_name
                 limit 100
            ), related as (
                select ranked.customer_code, ranked.customer_name_group,
                       json_agg(
                           json_build_object(
                               'post_id', post.post_id::text,
                               'post_title', post.post_title
                           )
                           order by ranked.created_at desc, ranked.post_id desc
                       ) as related_posts
                  from ranked
                  join top_groups
                    on top_groups.customer_code is not distinct from ranked.customer_code
                   and top_groups.customer_name_group is not distinct from ranked.customer_name_group
                  join source_post post on post.post_id = ranked.post_id
                 where ranked.related_rank <= 20
                 group by ranked.customer_code, ranked.customer_name_group
            )
            select top_groups.customer_code, top_groups.customer_name, top_groups.post_count,
                   coalesce(related.related_posts, '[]'::json) as related_posts
              from top_groups
              left join related
                on related.customer_code is not distinct from top_groups.customer_code
               and related.customer_name_group is not distinct from top_groups.customer_name_group
             order by top_groups.post_count desc, top_groups.customer_code, top_groups.customer_name
            """,
            list(account.corporate_entity_ids),
            list(account.process_unit_ids),
        )
        source_author_rows = await conn.fetch(
            f"""
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
                   and (post.visibility_code = 'public' or (
                        post.corporate_entity_id = any($1::uuid[])
                        and (cardinality($2::uuid[]) = 0
                             or post.process_unit_id = any($2::uuid[]))))
                   and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
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
            ), keyman_mentions as (
                select ranked.author_code, ranked.author_account_id,
                       ranked.account_display_name, ranked.post_id,
                       person.person_id, person.person_name,
                       person.person_side_code, person.last_known_job_title
                  from ranked
                  join post_summary_role role
                    on role.post_id = ranked.post_id
                   and role.actor_type_code = 'prov_person'
                  join cataloged_person person
                    on person.person_id = role.cataloged_person_id
                   and person.person_side_code = 'our_side'
                 where role.cataloged_person_id is not null
                union
                select ranked.author_code, ranked.author_account_id,
                       ranked.account_display_name, ranked.post_id,
                       person.person_id, person.person_name,
                       person.person_side_code, person.last_known_job_title
                  from ranked
                  join post_person_mention mention
                    on mention.post_id = ranked.post_id
                  join cataloged_person person
                    on person.person_id = mention.person_id
                   and person.person_side_code = 'our_side'
            ), keyman_authors as (
                select distinct author_code, author_account_id, account_display_name
                  from keyman_mentions
            ), top_groups as materialized (
                select groups.*
                  from groups
                  left join keyman_authors
                    on keyman_authors.author_code = groups.author_code
                   and keyman_authors.author_account_id = groups.author_account_id
                   and keyman_authors.account_display_name = groups.account_display_name
                 order by (keyman_authors.author_code is not null) desc,
                          groups.post_count desc, groups.author_code
                 limit 100
            ), keyman_groups as (
                select mentions.author_code, mentions.author_account_id,
                       mentions.account_display_name,
                       mentions.person_id, mentions.person_name,
                       mentions.person_side_code, mentions.last_known_job_title,
                       count(distinct mentions.post_id) as mention_count
                  from keyman_mentions mentions
                  join top_groups
                    on top_groups.author_code = mentions.author_code
                   and top_groups.author_account_id = mentions.author_account_id
                   and top_groups.account_display_name = mentions.account_display_name
                 group by mentions.author_code, mentions.author_account_id,
                          mentions.account_display_name, mentions.person_id,
                          mentions.person_name, mentions.person_side_code,
                          mentions.last_known_job_title
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
                               'post_person_mention.person_id|post_summary_role.cataloged_person_id/source_post.author_account_id'
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
                               'post_title', post.post_title
                           )
                           order by ranked.created_at desc, ranked.post_id desc
                       ) as related_posts
                  from ranked
                  join top_groups
                    on top_groups.author_code = ranked.author_code
                   and top_groups.author_account_id = ranked.author_account_id
                   and top_groups.account_display_name = ranked.account_display_name
                  join source_post post on post.post_id = ranked.post_id
                 where ranked.related_rank <= 20
                 group by ranked.author_code, ranked.author_account_id, ranked.account_display_name
            )
            select top_groups.author_code, top_groups.author_name, top_groups.author_account_id,
                   top_groups.account_display_name, top_groups.post_count,
                   coalesce(keyman_related.keyman_hints, '[]'::json) as keyman_hints,
                   coalesce(related.related_posts, '[]'::json) as related_posts
              from top_groups
              left join keyman_related
                on keyman_related.author_code = top_groups.author_code
               and keyman_related.author_account_id = top_groups.author_account_id
               and keyman_related.account_display_name = top_groups.account_display_name
              left join related
                on related.author_code = top_groups.author_code
               and related.author_account_id = top_groups.author_account_id
               and related.account_display_name = top_groups.account_display_name
             order by top_groups.post_count desc, top_groups.author_code
            """,
            list(account.corporate_entity_ids),
            list(account.process_unit_ids),
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
            has_source_context = await has_real_source_context(
                conn, list(account.corporate_entity_ids)
            )
        if has_source_context:
            synthetic_only_entity_ids = await fetch_demo_corporate_entity_ids(conn)
            entity_rows = [
                row
                for row in entity_rows
                if str(row["corporate_entity_id"]) not in synthetic_only_entity_ids
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
        side_labels = await labels_for_codes(conn, [row["person_side_code"] for row in keyman_rows])
        entity_level_labels = await labels_for_codes(conn, [row["entity_level_code"] for row in entity_rows])
        relationship_network = await fetch_relationship_network(conn, entity_ids)

    keymen_by_id: dict[str, dict[str, Any]] = {}
    for row in keyman_rows:
        person_id = str(row["person_id"])
        keyman = keymen_by_id.setdefault(
            person_id,
            {
                "person_id": person_id,
                "person_name": row["person_name"],
                "person_side_code": row["person_side_code"],
                "person_side_label": side_labels.get(row["person_side_code"], row["person_side_code"]),
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
                "entity_level_label": entity_level_labels.get(
                    row["entity_level_code"], row["entity_level_code"]
                ),
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
                "hint_trust": customer_hint_trust(row["customer_name"], row["customer_code"]),
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
        "relationship_network": relationship_network,
    }


@app.post("/api/customer-master/resolve-hint")
async def resolve_customer_master_hint(
    request: CustomerHintResolveRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    _require_post_admin(account)
    async with pool.acquire() as conn:
        try:
            resolution = await resolve_customer_hint(
                conn,
                _customer_hint_resolution_client(),
                _relation_verification_client(),
                request.hint_code,
            )
        except (HttpClientError, OSError) as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Hint resolution is unavailable: the orchestrator or search provider did not respond",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Hint resolution is unavailable: the orchestrator or search provider did not respond",
            ) from exc
    if resolution is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "this hint could not be resolved to a corroborated organization name",
        )
    return resolution


@app.get("/api/lineage")
async def read_lineage_graph(
    limit: int = Query(500, ge=1, le=2000),
    post_id: str | None = Query(None, min_length=1),
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    _require_post_read(account)
    async with pool.acquire() as conn:
        return await visible_lineage_graph(
            conn,
            lambda row: _can_see_post(account, row),
            limit=limit,
            focus_post_id=post_id,
            corporate_entity_ids=account.corporate_entity_ids,
            process_unit_ids=account.process_unit_ids,
        )


@app.post("/api/lineage/rebuild")
async def rebuild_lineage_graph(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    _require_post_admin(account)
    try:
        edges = await rebuild_lineage_from_pool(pool, llm=_adjudication_client())
    except ChannelWeightsNotEstimated as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Channel weights are not estimated yet. Run scripts/estimate_channel_weights.py, then rebuild again.",
        ) from exc
    except (AdjudicationClientError, HttpClientError, OSError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Lineage rebuild is unavailable: the orchestrator did not respond",
        ) from exc
    return {"edge_count": len(edges)}


# Remaining endpoint implementations are unchanged from the current branch head.
