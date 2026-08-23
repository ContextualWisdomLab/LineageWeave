"""Promote repeated customer hints into governed cross-post identity (ADR 0137)."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import asyncpg
from fast_mlsirm import LLMJudgeResult

from backend.app.corporate_entity_ingestion import get_or_create_corporate_entity
from backend.app.knowledge_graph import persist_edges_for_post
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.corporate_hierarchy_inference import CorporateHierarchyInferenceClient
from lineageweave.corporate_hierarchy_resolution import CorporateEntityCandidate
from lineageweave.customer_hint_resolution import CustomerHintResolutionClient
from lineageweave.customer_identity_judgment import (
    RUBRIC_VERSION,
    CustomerIdentityJudgeClient,
    identity_is_promotable,
    rename_is_supported,
)
from lineageweave.image_content import NullImageContentClient
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.organization_name_resolution import (
    resolve_and_verify_organization_name,
)
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_evaluation import irt_responses_from_result
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    RelationVerificationClient,
)
from lineageweave.tepp_client import (
    TemporalContextEvent,
    TemporalContextRequest,
    TeppClient,
    TeppNotAvailable,
)

_EXCERPT_LENGTH = 1500
_MAX_EVIDENCE_POSTS = 12
_STATUS_ABSTAINED = "customer_identity_abstained"
_STATUS_PROMOTED = "customer_identity_promoted"


def _iso8601(value: object) -> str:
    """Return an explicit UTC-aware ISO timestamp from a persisted source value."""
    if not isinstance(value, datetime):
        raise TypeError("customer identity evidence requires datetime source clocks")
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _evidence_records(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Normalize bounded post excerpts once for fingerprinting and judging."""
    vision_client = NullImageContentClient()
    records: list[dict[str, Any]] = []
    for row in rows:
        excerpt = normalize_post_body(
            row["post_body"], vision_client=vision_client
        ).text[:_EXCERPT_LENGTH]
        records.append(
            {
                "post_id": str(row["post_id"]),
                "post_title": row["post_title"],
                "excerpt": excerpt,
                "excerpt_sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
                "source_customer_name": row.get("source_customer_name"),
                "created_at": _iso8601(row["created_at"]),
                "updated_at": _iso8601(row["updated_at"]),
            }
        )
    return records


def _evidence_sha256(records: Sequence[Mapping[str, Any]]) -> str:
    """Fingerprint evidence without persisting a second copy of source text."""
    fingerprint_rows = [
        {
            "post_id": record["post_id"],
            "source_customer_name": record["source_customer_name"],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
            "excerpt_sha256": record["excerpt_sha256"],
        }
        for record in sorted(records, key=lambda item: str(item["post_id"]))
    ]
    payload = json.dumps(fingerprint_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _judge_context(
    records: Sequence[Mapping[str, Any]],
    source_system_code: str | None,
    source_customer_code: str,
) -> str:
    """Render explicit record boundaries so a judge cannot count one post twice."""
    system = source_system_code if source_system_code is not None else "(source system absent)"
    return "\n\n---\n\n".join(
        (
            f"record_ordinal={ordinal}\n"
            f"post_id={record['post_id']}\n"
            f"source_system_code={system}\n"
            f"source_customer_code={source_customer_code}\n"
            f"source_customer_name={record['source_customer_name'] or '(absent)'}\n"
            f"created_at={record['created_at']}\n"
            f"updated_at={record['updated_at']}\n"
            f"title={record['post_title']}\n"
            f"excerpt={record['excerpt']}"
        )
        for ordinal, record in enumerate(records)
    )


async def _temporally_order_records(
    records: list[dict[str, Any]],
    tepp_client: TeppClient | None,
    source_system_code: str | None,
    source_customer_code: str,
) -> tuple[list[dict[str, Any]], str]:
    """Use TEPP ordering when available; otherwise retain source-clock order."""
    source_order = sorted(records, key=lambda row: (row["created_at"], row["post_id"]))
    if tepp_client is None:
        return source_order, "source_timestamp"
    actor_digest = hashlib.sha256(
        f"{source_system_code or ''}\0{source_customer_code}".encode()
    ).hexdigest()
    events = tuple(
        TemporalContextEvent(
            event_id=f"customer-observation:{record['post_id']}",
            source_post_id=str(record["post_id"]),
            event_type_code="customer_identity_observation",
            event_label="Customer identity observation",
            event_time=str(record["created_at"]),
            available_time=str(record["updated_at"]),
            project_reference=None,
            actor_references=(f"customer-key:{actor_digest}",),
        )
        for record in source_order
    )
    request = TemporalContextRequest(
        knowledge_cutoff=max(str(record["updated_at"]) for record in source_order),
        subject_post_id=str(source_order[-1]["post_id"]),
        events=events,
    )
    try:
        response = await asyncio.to_thread(tepp_client.temporal_context, request)
    except TeppNotAvailable:
        return source_order, "source_timestamp"
    by_post_id = {str(record["post_id"]): record for record in source_order}
    return [by_post_id[post_id] for post_id in response["source_post_ids"]], "tepp"


async def _cached_promotion(
    conn: asyncpg.Connection,
    source_system_code: str | None,
    source_customer_code: str,
    evidence_sha256: str,
) -> dict[str, Any] | None:
    """Reuse an unchanged promoted decision without paying for another judge call."""
    row = await conn.fetchrow(
        """
        select judgment.customer_identity_judgment_id,
               entity.corporate_entity_id, entity.entity_name,
               judgment.distinct_post_count, judgment.verification_evidence_url
          from customer_identity_judgment judgment
          join customer_identity_binding binding
            on binding.customer_identity_judgment_id = judgment.customer_identity_judgment_id
          join corporate_entity entity
            on entity.corporate_entity_id = binding.corporate_entity_id
         where judgment.source_system_code is not distinct from $1
           and judgment.source_customer_code = $2
           and judgment.evidence_sha256 = $3
           and judgment.rubric_version = $4
           and judgment.judgment_status_code = $5
        """,
        source_system_code,
        source_customer_code,
        evidence_sha256,
        RUBRIC_VERSION,
        _STATUS_PROMOTED,
    )
    if row is None:
        return None
    return {
        "corporate_entity_id": str(row["corporate_entity_id"]),
        "entity_name": row["entity_name"],
        "linked_post_count": row["distinct_post_count"],
        "verification_evidence_url": row["verification_evidence_url"],
        "customer_identity_judgment_id": str(row["customer_identity_judgment_id"]),
        "resolution_status": _STATUS_PROMOTED,
        "cached": True,
    }


async def _persist_judgment(
    conn: asyncpg.Connection,
    *,
    source_system_code: str | None,
    source_customer_code: str,
    candidate_name: str,
    evidence_sha256: str,
    records: Sequence[Mapping[str, Any]],
    result: LLMJudgeResult,
    temporal_order_source_code: str,
    verification_evidence_url: str | None,
) -> str:
    """Persist the decision, its IRT row, and exact supporting posts."""
    row = await conn.fetchrow(
        """
        insert into customer_identity_judgment (
            source_system_code, source_customer_code, candidate_entity_name,
            evidence_sha256, judgment_status_code, rubric_version,
            distinct_post_count, judge_score, judge_accepted, judge_rationale,
            orchestration_mode, trace_step_count, temporal_order_source_code,
            verification_evidence_url
        ) values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        on conflict on constraint customer_identity_judgment_evidence_unique
        do update set candidate_entity_name = excluded.candidate_entity_name,
                      judgment_status_code = excluded.judgment_status_code,
                      distinct_post_count = excluded.distinct_post_count,
                      judge_score = excluded.judge_score,
                      judge_accepted = excluded.judge_accepted,
                      judge_rationale = excluded.judge_rationale,
                      orchestration_mode = excluded.orchestration_mode,
                      trace_step_count = excluded.trace_step_count,
                      temporal_order_source_code = excluded.temporal_order_source_code,
                      verification_evidence_url = excluded.verification_evidence_url,
                      judged_at = now()
        returning customer_identity_judgment_id
        """,
        source_system_code,
        source_customer_code,
        candidate_name,
        evidence_sha256,
        _STATUS_ABSTAINED,
        RUBRIC_VERSION,
        len(records),
        result.score,
        result.accepted,
        result.rationale,
        result.orchestration_mode,
        result.trace_step_count,
        temporal_order_source_code,
        verification_evidence_url,
    )
    judgment_id = str(row["customer_identity_judgment_id"])
    for response in irt_responses_from_result(result):
        await conn.execute(
            """
            insert into customer_identity_judgment_response (
                customer_identity_judgment_id, criterion_code,
                criterion_score, response_category
            ) values ($1, $2, $3, $4)
            on conflict (customer_identity_judgment_id, criterion_code)
            do update set criterion_score = excluded.criterion_score,
                          response_category = excluded.response_category
            """,
            judgment_id,
            response.criterion_code,
            result.criterion_scores[response.criterion_code],
            response.response_category,
        )
    for ordinal, record in enumerate(records):
        await conn.execute(
            """
            insert into customer_identity_judgment_post (
                customer_identity_judgment_id, post_id, evidence_ordinal,
                observed_customer_name, excerpt_sha256
            ) values ($1, $2, $3, $4, $5)
            on conflict (customer_identity_judgment_id, post_id)
            do update set evidence_ordinal = excluded.evidence_ordinal,
                          observed_customer_name = excluded.observed_customer_name,
                          excerpt_sha256 = excluded.excerpt_sha256
            """,
            judgment_id,
            record["post_id"],
            ordinal,
            record["source_customer_name"],
            record["excerpt_sha256"],
        )
    return judgment_id


async def _bound_entity(
    conn: asyncpg.Connection,
    source_system_code: str | None,
    source_customer_code: str,
) -> Mapping[str, Any] | None:
    """Load the stable Customer Master binding for one exact source key."""
    return await conn.fetchrow(
        """
        select entity.corporate_entity_id, entity.entity_name
          from customer_identity_binding binding
          join corporate_entity entity using (corporate_entity_id)
         where binding.source_system_code is not distinct from $1
           and binding.source_customer_code = $2
        """,
        source_system_code,
        source_customer_code,
    )


async def _catalog_entity(
    conn: asyncpg.Connection,
    candidate_name: str,
    context_text: str,
    inference_client: CorporateHierarchyInferenceClient | None,
    verification_client: RelationVerificationClient,
) -> str | None:
    """Reuse ADR 0010/0012/0026 rather than creating a second catalog path."""
    rows = await conn.fetch("select corporate_entity_id, entity_name from corporate_entity")
    candidates = [
        CorporateEntityCandidate(str(row["corporate_entity_id"]), row["entity_name"])
        for row in rows
    ]
    if inference_client is None:
        return None
    entity_id, _unresolved_reason = await get_or_create_corporate_entity(
        conn,
        candidate_name,
        context_text,
        inference_client,
        verification_client,
        candidates,
    )
    return entity_id


async def _record_name(
    conn: asyncpg.Connection,
    entity_id: str,
    candidate_name: str,
    judgment_id: str,
    observed_from: datetime,
    rename_result: LLMJudgeResult | None,
) -> str:
    """Preserve aliases and replace a preferred name only on strict rename proof."""
    entity = await conn.fetchrow(
        "select entity_name, created_at from corporate_entity where corporate_entity_id = $1",
        entity_id,
    )
    current_name = entity["entity_name"]
    await conn.execute(
        """
        insert into corporate_entity_name_history (
            corporate_entity_id, entity_name, name_role_code, observed_from
        )
        select $1, $2, 'entity_name_preferred', $3
         where not exists (
             select 1 from corporate_entity_name_history
              where corporate_entity_id = $1
                and name_role_code = 'entity_name_preferred'
                and observed_to is null
         )
        """,
        entity_id,
        current_name,
        entity["created_at"],
    )
    if current_name.casefold() == candidate_name.casefold():
        return current_name
    if rename_result is not None and rename_is_supported(rename_result):
        await conn.execute(
            """
            update corporate_entity_name_history
               set name_role_code = 'entity_name_former', observed_to = $2
             where corporate_entity_id = $1
               and name_role_code = 'entity_name_preferred'
               and observed_to is null
            """,
            entity_id,
            observed_from,
        )
        await conn.execute(
            "update corporate_entity set entity_name = $2 where corporate_entity_id = $1",
            entity_id,
            candidate_name,
        )
        await conn.execute(
            """
            insert into corporate_entity_name_history (
                corporate_entity_id, entity_name, name_role_code,
                observed_from, customer_identity_judgment_id
            ) values ($1, $2, 'entity_name_preferred', $3, $4)
            """,
            entity_id,
            candidate_name,
            observed_from,
            judgment_id,
        )
        return candidate_name
    await conn.execute(
        """
        insert into corporate_entity_name_history (
            corporate_entity_id, entity_name, name_role_code,
            observed_from, customer_identity_judgment_id
        )
        select $1, $2, 'entity_name_alternate', $3, $4
         where not exists (
             select 1 from corporate_entity_name_history
              where corporate_entity_id = $1 and lower(entity_name) = lower($2)
         )
        """,
        entity_id,
        candidate_name,
        observed_from,
        judgment_id,
    )
    return current_name


async def _persist_rename_result(
    conn: asyncpg.Connection,
    judgment_id: str,
    result: LLMJudgeResult,
) -> None:
    """Attach the separate strict rename judgment to the same evidence run."""
    await conn.execute(
        """
        update customer_identity_judgment
           set rename_judge_score = $2,
               rename_judge_accepted = $3,
               rename_judge_rationale = $4
         where customer_identity_judgment_id = $1
        """,
        judgment_id,
        result.score,
        result.accepted,
        result.rationale,
    )
    for response in irt_responses_from_result(result):
        await conn.execute(
            """
            insert into customer_identity_judgment_response (
                customer_identity_judgment_id, criterion_code,
                criterion_score, response_category
            ) values ($1, $2, $3, $4)
            on conflict (customer_identity_judgment_id, criterion_code)
            do update set criterion_score = excluded.criterion_score,
                          response_category = excluded.response_category
            """,
            judgment_id,
            response.criterion_code,
            result.criterion_scores[response.criterion_code],
            response.response_category,
        )


async def resolve_customer_hint(
    conn: asyncpg.Connection,
    resolution_client: CustomerHintResolutionClient,
    verification_client: RelationVerificationClient,
    hint_code: str,
    *,
    source_system_code: str | None = None,
    authorized_corporate_entity_ids: Sequence[str] = (),
    identity_judge_client: CustomerIdentityJudgeClient | None = None,
    hierarchy_inference_client: CorporateHierarchyInferenceClient | None = None,
    tepp_client: TeppClient | None = None,
) -> dict[str, Any] | None:
    """Promote one exact source-system/customer-code key after collective proof."""
    normalized_hint = hint_code.strip()
    if (
        not normalized_hint
        or not resolution_client.available
        or identity_judge_client is None
        or not identity_judge_client.available
        or not authorized_corporate_entity_ids
    ):
        return None
    # Safe SQL: eligibility is a closed schema fragment; all customer and scope values are bound.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post.post_id, post.post_title, left(post_body, 20000) as post_body,
               post.source_customer_name, post.created_at, post.updated_at,
               post.author_account_id, entity.corporate_entity_code,
               post.source_process_unit_code, post.source_author_code,
               post.source_company_code, post.source_customer_code,
               post.source_project_code, post.source_sales_pool_code,
               post.source_system_code, post.visibility_code
          from source_post post
          join corporate_entity entity using (corporate_entity_id)
         where nullif(btrim(post.source_customer_code), '') = $1
           and post.source_system_code is not distinct from $2
           and (post.visibility_code = 'public' or post.corporate_entity_id = any($3::uuid[]))
           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
         order by post.created_at, post.post_id
         limit $4
        """,
        normalized_hint,
        source_system_code,
        list(authorized_corporate_entity_ids),
        _MAX_EVIDENCE_POSTS,
    )
    if len({str(row["post_id"]) for row in rows}) < 2:
        return None

    records = _evidence_records(rows)
    evidence_sha256 = _evidence_sha256(records)
    cached = await _cached_promotion(
        conn, source_system_code, normalized_hint, evidence_sha256
    )
    if cached is not None:
        return cached
    records, temporal_source = await _temporally_order_records(
        records, tepp_client, source_system_code, normalized_hint
    )
    context_text = _judge_context(records, source_system_code, normalized_hint)
    subject = max(rows, key=lambda row: (row["updated_at"], str(row["post_id"])))
    metadata = build_post_llm_metadata(str(subject["post_id"]), subject)
    metadata.update(
        {
            "lineageweave_source_system_code": source_system_code or "",
            "lineageweave_visibility": subject.get("visibility_code") or "",
            "lineageweave_customer_evidence_sha256": evidence_sha256,
        }
    )
    with use_llm_metadata(metadata):
        resolution = await asyncio.to_thread(
            resolve_and_verify_organization_name,
            normalized_hint,
            context_text,
            resolution_client,
            verification_client,
        )
    if resolution is None:
        return None
    with use_llm_metadata(metadata):
        identity_result = await asyncio.to_thread(
            identity_judge_client.judge_identity,
            resolution.resolved_organization_name,
            context_text,
        )
    judgment_id = await _persist_judgment(
        conn,
        source_system_code=source_system_code,
        source_customer_code=normalized_hint,
        candidate_name=resolution.resolved_organization_name,
        evidence_sha256=evidence_sha256,
        records=records,
        result=identity_result,
        temporal_order_source_code=temporal_source,
        verification_evidence_url=resolution.verification_evidence_url,
    )
    if (
        resolution.verification_status_code != STATUS_CORROBORATED
        or not identity_is_promotable(identity_result, len(records))
    ):
        return None

    binding = await _bound_entity(conn, source_system_code, normalized_hint)
    if binding is None:
        entity_id = await _catalog_entity(
            conn,
            resolution.resolved_organization_name,
            context_text,
            hierarchy_inference_client,
            verification_client,
        )
        if entity_id is None:
            return None
        previous_name = resolution.resolved_organization_name
    else:
        entity_id = str(binding["corporate_entity_id"])
        previous_name = binding["entity_name"]

    rename_result: LLMJudgeResult | None = None
    if previous_name.casefold() != resolution.resolved_organization_name.casefold():
        with use_llm_metadata(metadata):
            rename_result = await asyncio.to_thread(
                identity_judge_client.judge_rename,
                previous_name,
                resolution.resolved_organization_name,
                context_text,
            )
        await _persist_rename_result(conn, judgment_id, rename_result)

    observed_from = max(row["created_at"] for row in rows)
    async with conn.transaction():
        binding_row = await conn.fetchrow(
            """
            insert into customer_identity_binding (
                source_system_code, source_customer_code,
                corporate_entity_id, customer_identity_judgment_id
            ) values ($1, $2, $3, $4)
            on conflict on constraint customer_identity_binding_source_unique
            do update set customer_identity_judgment_id = excluded.customer_identity_judgment_id,
                          updated_at = now()
            returning corporate_entity_id
            """,
            source_system_code,
            normalized_hint,
            entity_id,
            judgment_id,
        )
        entity_id = str(binding_row["corporate_entity_id"])
        display_name = await _record_name(
            conn,
            entity_id,
            resolution.resolved_organization_name,
            judgment_id,
            observed_from,
            rename_result,
        )
        for record in records:
            await conn.execute(
                """
                insert into post_customer_identity_mention (
                    post_id, corporate_entity_id, customer_identity_judgment_id
                ) values ($1, $2, $3)
                on conflict (post_id, corporate_entity_id)
                do update set customer_identity_judgment_id = excluded.customer_identity_judgment_id
                """,
                record["post_id"],
                entity_id,
                judgment_id,
            )
        await conn.execute(
            """
            update customer_identity_judgment
               set judgment_status_code = $2, corporate_entity_id = $3
             where customer_identity_judgment_id = $1
            """,
            judgment_id,
            _STATUS_PROMOTED,
            entity_id,
        )
        for record in records:
            await persist_edges_for_post(conn, str(record["post_id"]))
    return {
        "corporate_entity_id": entity_id,
        "entity_name": display_name,
        "linked_post_count": len(records),
        "verification_evidence_url": resolution.verification_evidence_url,
        "customer_identity_judgment_id": judgment_id,
        "resolution_status": _STATUS_PROMOTED,
        "cached": False,
    }


async def reconcile_customer_hints(
    conn: asyncpg.Connection,
    resolution_client: CustomerHintResolutionClient,
    verification_client: RelationVerificationClient,
    source_keys: Sequence[tuple[str | None, str]],
    *,
    authorized_corporate_entity_ids: Sequence[str],
    identity_judge_client: CustomerIdentityJudgeClient,
    hierarchy_inference_client: CorporateHierarchyInferenceClient,
    tepp_client: TeppClient | None = None,
) -> dict[str, int]:
    """Evaluate changed source keys after import without failing the import on provider outages."""
    keys = sorted({(system, code.strip()) for system, code in source_keys if code.strip()})
    counts = {"candidates": len(keys), "promoted": 0, "unresolved": 0, "unavailable": 0}
    if not (
        resolution_client.available
        and verification_client.available
        and identity_judge_client.available
        and hierarchy_inference_client.available
    ):
        counts["unavailable"] = len(keys)
        return counts
    for source_system_code, source_customer_code in keys:
        try:
            result = await resolve_customer_hint(
                conn,
                resolution_client,
                verification_client,
                source_customer_code,
                source_system_code=source_system_code,
                authorized_corporate_entity_ids=authorized_corporate_entity_ids,
                identity_judge_client=identity_judge_client,
                hierarchy_inference_client=hierarchy_inference_client,
                tepp_client=tepp_client,
            )
        except asyncpg.PostgresError:
            raise
        except Exception:  # noqa: BLE001 - one provider failure must not block other source keys.
            counts["unavailable"] += 1
            continue
        counts["promoted" if result is not None else "unresolved"] += 1
    return counts
