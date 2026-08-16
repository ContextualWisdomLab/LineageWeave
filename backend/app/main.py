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
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lineageweave.commitment_extraction import (
    ContextualOrchestratorCommitmentExtractionClient,
    NullCommitmentExtractionClient,
)
from lineageweave.entity_relationship_classification import (
    ContextualOrchestratorEntityRelationshipClient,
    NullEntityRelationshipClient,
)
from lineageweave.image_content import orchestrator_vision_client
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

from backend.app.analysis_run_ingestion import (
    AnalysisRunCreateError,
    create_pending_analysis_run,
    fetch_visible_analysis_run,
    fetch_visible_analysis_runs,
)
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
from backend.app.post_evaluation_ingestion import fetch_post_evaluation, ingest_post_evaluation
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
    visible_affiliation_post_ids,
    visible_mention_post_ids,
)
from backend.app.lineage_ingestion import rebuild_lineage, visible_lineage_graph
from backend.app.post_chat_ingestion import (
    fetch_persisted_chat,
    fetch_persisted_chats,
    find_linked_post_ids,
    gather_chat_sources,
    persist_post_chat,
)
from backend.app.post_summary_ingestion import fetch_persisted_summary, persist_post_summary

_POST_READ = "post_read"
_POST_ADMIN = "post_admin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open one asyncpg pool and one Valkey client for the process, and
    close both on shutdown."""
    settings = load_settings()
    app.state.pool = await create_pool(settings.database_url)
    app.state.valkey = create_valkey_client(settings.valkey_url)
    try:
        yield
    finally:
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


def _post_evaluation_client():
    """Live judge client when configured; otherwise the unavailable null."""
    settings = load_settings()
    if not (settings.orchestrator_base_url and settings.orchestrator_api_key):
        return NullPostEvaluationClient()
    return ContextualOrchestratorPostEvaluationClient(
        base_url=settings.orchestrator_base_url, api_key=settings.orchestrator_api_key
    )


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
    return {
        "post_id": str(post["post_id"]),
        "post_title": post["post_title"],
        "voc_type_code": voc,
        "voc_type_label": resolved.get(voc, voc),
        "visibility_code": visibility,
        "visibility_label": resolved.get(visibility, visibility),
        "created_at": post["created_at"].isoformat(),
    }


async def _lookup_post_labels(conn: asyncpg.Connection, rows: list[asyncpg.Record]) -> dict[str, str]:
    """Resolve voc_type / visibility codes against common_lookup_value."""
    codes = [row["voc_type_code"] for row in rows] + [row["visibility_code"] for row in rows]
    return await labels_for_codes(conn, codes)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe: the process is up. Does not touch Postgres."""
    return {"status": "ok"}


@app.get("/api/me")
async def read_me(account: CurrentAccount = Depends(get_current_account)) -> dict[str, Any]:
    """Return the provisioned account that the bearer token resolved to."""
    return {
        "user_account_id": account.user_account_id,
        "display_name": account.display_name,
        "permission_codes": sorted(account.permission_codes),
    }


@app.get("/api/lineage")
async def read_lineage_graph(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """ABAC-filtered reconstruct graph for the product UI (same shape as the demo server)."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        return await visible_lineage_graph(conn, lambda row: _can_see_post(account, row))


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
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict[str, Any]]:
    """List source_post rows the account is allowed to see (RBAC then ABAC)."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "select post_id, post_title, voc_type_code, visibility_code, corporate_entity_id, created_at "
            "from source_post order by created_at desc"
        )
        visible = [row for row in rows if _can_see_post(account, row)]
        labels = await _lookup_post_labels(conn, visible)
    return [_serialize_post(row, labels) for row in visible]


@app.get("/api/posts/{post_id}")
async def read_post(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Return one source_post, or 404 / 403 if it is missing or out of scope."""
    _require_post_read(account)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select post_id, post_title, post_body, voc_type_code, visibility_code, corporate_entity_id, created_at "
            "from source_post where post_id = $1",
            post_id,
        )
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "post not found")
        if not _can_see_post(account, row):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized to view this post")
        labels = await _lookup_post_labels(conn, [row])
    return {**_serialize_post(row, labels), "post_body": row["post_body"]}


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
    return {"post_id": str(post["post_id"]), "keymen": keymen}


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
        verified = await verify_post_relations(conn, client, post_id)
    return {
        "post_id": str(post["post_id"]),
        "verified": [
            {
                "counterparty_entity_name": row.counterparty_entity_name,
                "verification_status_code": row.verification_status_code,
                "verification_evidence_url": row.verification_evidence_url,
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
        mentions = await ingest_post_keymen(
            conn,
            keyman_client,
            post_id,
            post["post_title"],
            post_body,
            resolution_client=_organization_name_resolution_client(),
            verification_client=_relation_verification_client(),
            hierarchy_inference_client=_corporate_hierarchy_inference_client(),
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
                "select post_id, post_title, visibility_code, corporate_entity_id "
                "from source_post where post_id = any($1::uuid[])",
                list(candidate_ids),
            )
            rows = {str(row["post_id"]): row for row in fetched}

    def _visible_summaries(ids: frozenset[str]) -> list[dict[str, Any]]:
        return [
            {"post_id": post_id_, "post_title": rows[post_id_]["post_title"]}
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
        visible.append({**report, "members": members, "post_count": len(members)})
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
        stored = await fetch_persisted_summary(conn, post_id)
        if stored is not None:
            return stored
        client = _post_summary_client()
        if not client.available:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Post summary is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
            )
        body_row = await conn.fetchrow("select post_body from source_post where post_id = $1", post_id)
        normalized_body = normalize_post_body(body_row["post_body"], vision_client=_vision_client()).text
        summary = await asyncio.to_thread(
            client.summarize, post["post_title"], normalized_body
        )
        return await persist_post_summary(
            conn,
            post_id,
            summary,
            post_body=normalized_body,
            hierarchy_inference_client=_corporate_hierarchy_inference_client(),
            verification_client=_relation_verification_client(),
        )


class ChatRequest(BaseModel):
    """JSON body for ``POST /api/posts/{post_id}/chat``."""

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
    answer = client.answer(question, sources)
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
    Reconstruction and TEPP execution stay later slices; this write
    records Pending only.
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
    """Record a Pending analysis run on an authorized cutoff capture.

    post_read is enough: the caller requests a run of a corp they
    already walk. The payload is the same authorized detail as GET.
    Hidden scopes 404. A matching idempotent retry returns the same run.
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
    """Every dated, not-closed commitment/ticket the account may see,
    soonest first -- the to-do/calendar surface (no Outlook sync yet;
    this is the internal data model that a future Outlook connector
    would read from).
    """
    _require_post_read(account)
    async with pool.acquire() as conn:
        commitments = await fetch_upcoming_commitments(conn)
    visible = [c for c in commitments if _can_see_post(account, c)]
    for c in visible:
        del c["visibility_code"], c["corporate_entity_id"]
    return {"commitments": visible}
