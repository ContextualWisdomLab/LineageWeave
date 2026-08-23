"""Persist and load the popup's Korean summary / key events / R&R.

ADR 0009 / 0019 / 0027: an R&R actor is not just per-post free text --
when it is a team, organization, or already-cataloged person, it is
resolved to a shared catalog identity (``cataloged_team`` /
``corporate_entity`` / ``cataloged_person``) stored on the role row and
a Knowledge Graph mention edge is written, so the same "설계팀" or
organization named across two posts becomes one linkable node. Fetch
never reconstructs that id by ``entity_name`` or ``person_name``; those
columns are not unique. A person actor is opportunistically joined to
an *existing* ``cataloged_person`` row by name when Keyman extraction
has already cataloged that name. The resolved ``cataloged_person_id``
is stored on the role so a later read does not rejoin by display name.
The R&R evidence is written to ``post_summary_person_mention`` rather
than Keyman's ``post_person_mention`` so either extractor can replace
its own result without leaving or deleting the other's evidence.

ADR 0010: an organization actor's name is resolved via
``get_or_create_corporate_entity`` -- similarity matching first, then
an LLM-proposed, search-corroborated hierarchy placement before
creating a real new row, so a real dataset's first mention of a
counterparty organization actually populates the corporate hierarchy
tree instead of staying permanently unresolved.  Inference,
verification, and the short advisory-lock creation transaction finish
before the summary-replacement transaction begins; slow external work
therefore cannot extend the lock or the atomic replacement window.
"""

from __future__ import annotations

import hashlib
from typing import Any

import asyncpg

from lineageweave.corporate_hierarchy_inference import (
    CorporateHierarchyInferenceClient,
    NullCorporateHierarchyInferenceClient,
)
from lineageweave.fixtures import fixture_thread_cast
from lineageweave.http_client import HttpClientError
from lineageweave.knowledge_graph import (
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_TEAM,
)
from lineageweave.ontology import (
    LW,
    ontology_annotations,
    semantic_predicate_annotations,
)
from lineageweave.organization_name_resolution import (
    NullOrganizationNameResolutionClient,
    OrganizationNameResolutionClient,
)
from lineageweave.post_summary import (
    ACTOR_TYPE_ORGANIZATION,
    ACTOR_TYPE_PERSON,
    ACTOR_TYPE_TEAM,
    POST_SUMMARY_CONTRACT_VERSION,
    KeyEvent,
    PostSummary,
    RoleResponsibility,
    is_generic_team_actor,
    normalize_project_key,
)
from lineageweave.relation_verification import (
    NullRelationVerificationClient,
    RelationVerificationClient,
)

from .corporate_entity_ingestion import (
    PreparedCorporateEntityResolution,
    apply_prepared_corporate_entity_resolution,
    prepare_corporate_entity_resolution,
)
from .keyman_ingestion import (
    PreparedAffiliatedOrganization,
    _load_corporate_entity_candidates,
    apply_prepared_affiliated_organization,
    prepare_affiliated_organization,
)
from .knowledge_graph import persist_edges_for_post
from .post_content_queue import SUCCEEDED, fetch_post_summary_source, source_body_sha256
from .post_eligibility import normalize_source_detail_state_code
from .team_ingestion import upsert_team

SUMMARY_SOURCE_BODY_MISSING = (
    "Post summary is unavailable: the source post body is empty. "
    "Re-import the source record with its body before requesting a summary."
)
SUMMARY_TARGET_UNAVAILABLE = "Writing-in-progress posts are not summary targets."


def require_summary_source_body(body: str | None) -> str:
    """Reject summary derivation when the evidence body was not imported."""
    if not isinstance(body, str) or not body.strip():
        raise ValueError(SUMMARY_SOURCE_BODY_MISSING)
    return body


def summary_input_sha256(summary_input: str) -> str:
    """Bind a summary row to its exact normalized source/evidence text."""
    return hashlib.sha256(summary_input.encode("utf-8")).hexdigest()


async def require_summary_target(conn: asyncpg.Connection, post_id: str) -> None:
    """Keep W out of both persisted and on-demand summary generation."""
    state_code = await conn.fetchval(
        "select source_detail_state_code from source_post where post_id = $1",
        post_id,
    )
    if normalize_source_detail_state_code(state_code) == "W":
        raise ValueError(SUMMARY_TARGET_UNAVAILABLE)


async def _lock_current_summary_input(
    conn: asyncpg.Connection,
    post_id: str,
    *,
    expected_source_body_sha256: str,
    expected_summary_input: str,
    require_image_evidence: bool,
) -> bool:
    """Lock and recheck the exact source and persisted summary evidence."""
    row = await conn.fetchrow(
        "select post_body from source_post where post_id = $1 for update",
        post_id,
    )
    if row is None:
        return False
    current_body = row["post_body"]
    if not isinstance(current_body, str):
        return False
    if source_body_sha256(current_body) != expected_source_body_sha256:
        return False
    if not require_image_evidence:
        return True
    job = await conn.fetchrow(
        """
        select status_code
        from post_content_ingestion_job
        where post_id = $1
          and source_body_sha256 = $2
          and status_code = $3
        for update
        """,
        post_id,
        expected_source_body_sha256,
        SUCCEEDED,
    )
    if job is None:
        return False
    return await fetch_post_summary_source(conn, post_id) == expected_summary_input


async def fetch_persisted_summary(
    conn: asyncpg.Connection,
    post_id: str,
    *,
    summary_input: str | None = None,
    allow_stale: bool = False,
) -> dict[str, Any] | None:
    """Return the stored summary payload, or None when none is usable.

    ``catalog_node_id`` comes from the role row's catalog foreign keys
    (ADR 0019 / 0027). This function does not join ``corporate_entity``
    by ``entity_name``. Person chips read ``cataloged_person_id``. A stale
    row is returned only when ``allow_stale`` is explicit so a caller can
    preserve reader continuity without presenting old semantics as current.
    A current row additionally requires an exact normalized-input binding.
    """
    header = await conn.fetchrow(
        "select korean_summary, summary_contract_version, summary_input_sha256 "
        "from post_summary_result where post_id = $1",
        post_id,
    )
    if header is None:
        return None
    summary_contract_version = header["summary_contract_version"]
    input_matches = bool(
        summary_input is not None
        and header.get("summary_input_sha256") == summary_input_sha256(summary_input)
    )
    summary_is_current = (
        summary_contract_version == POST_SUMMARY_CONTRACT_VERSION and input_matches
    )
    if not summary_is_current and not allow_stale:
        return None
    events = await conn.fetch(
        """
        select event.event_ordinal, event.event_text, event.evidence_text,
               event.project_key, mention.project_name
          from post_summary_event event
          left join post_project_mention mention
            on mention.post_id = event.post_id
           and mention.project_key = event.project_key
         where event.post_id = $1
         order by event.event_ordinal
        """,
        post_id,
    )
    roles = await conn.fetch(
        """
        select role.actor_name, role.responsibility_text, role.actor_type_code,
               role.affiliated_organization_name,
               role.cataloged_team_id,
               role.cataloged_corporate_entity_id,
               role.cataloged_person_id,
               role.cataloged_affiliated_corporate_entity_id,
               role.catalog_unresolved_reason_code,
               role.affiliation_catalog_unresolved_reason_code
          from post_summary_role role
         where role.post_id = $1
         order by role.actor_name
        """,
        post_id,
    )
    projects = await conn.fetch(
        """
        select project_key, project_name, evidence_text, mention_confidence, ontology_iri,
               extraction_method
          from post_project_mention
         where post_id = $1
         order by project_name, project_key
        """,
        post_id,
    )
    actions = await conn.fetch(
        """
        select action.action_text, action.requester_actor_name,
               action.processor_actor_name, action.evidence_text,
               mention.project_name
          from post_summary_action action
          left join post_project_mention mention
            on mention.post_id = action.post_id
           and mention.project_key = action.project_key
         where action.post_id = $1
         order by action.action_ordinal
        """,
        post_id,
    )
    quantitative_observations = await conn.fetch(
        """
        select observation.measurement_type_code,
               observation.label_text,
               observation.value_numeric,
               observation.unit_code,
               observation.quantity_numeric,
               observation.quantity_unit_code,
               observation.qualifier_text,
               observation.raw_value_text,
               observation.evidence_text,
               observation.ontology_iri,
               observation.extraction_method
          from post_summary_quantitative_observation observation
         where observation.post_id = $1
         order by observation.observation_ordinal
        """,
        post_id,
    )
    source_grounded_facts = await conn.fetch(
        """
        select fact.fact_type_code,
               fact.label_text,
               fact.value_text,
               fact.normalized_value_text,
               fact.assertion_code,
               fact.normalized_date,
               fact.date_precision_code,
               fact.normalization_evidence_text,
               fact.qualifier_text,
               fact.evidence_text,
               fact.ontology_iri,
               fact.extraction_method
          from post_summary_source_fact fact
         where fact.post_id = $1
         order by fact.fact_ordinal
        """,
        post_id,
    )
    semantic_relationships = await conn.fetch(
        """
        select relation_ordinal, subject_name, subject_type, predicate_code,
               object_name, object_type, evidence_text, relation_confidence,
               extraction_method
          from post_summary_semantic_relationship
         where post_id = $1
         order by relation_ordinal
        """,
        post_id,
    )
    event_clues = await conn.fetch(
        """
        select event_ordinal, clue_ordinal, clue_type_code, clue_text,
               target_text, normalized_value_text, assertion_code,
               evidence_text, ontology_iri, extraction_method
          from post_summary_event_clue
         where post_id = $1
         order by event_ordinal, clue_ordinal
        """,
        post_id,
    )
    payload_roles: list[dict[str, Any]] = []
    for row in roles:
        catalog_node_id = None
        catalog_node_type_code = None
        if row["cataloged_team_id"] is not None:
            catalog_node_id = str(row["cataloged_team_id"])
            catalog_node_type_code = NODE_TEAM
        elif row["cataloged_corporate_entity_id"] is not None:
            catalog_node_id = str(row["cataloged_corporate_entity_id"])
            catalog_node_type_code = NODE_CORPORATE_ENTITY
        elif row["cataloged_person_id"] is not None:
            catalog_node_id = str(row["cataloged_person_id"])
            catalog_node_type_code = NODE_PERSON
        payload_roles.append(
            {
                "actor_name": row["actor_name"],
                "responsibility": row["responsibility_text"],
                "actor_type_code": row["actor_type_code"],
                "affiliated_organization_name": row["affiliated_organization_name"],
                "catalog_node_id": catalog_node_id,
                "catalog_node_type_code": catalog_node_type_code,
                "affiliated_organization_catalog_id": (
                    str(row["cataloged_affiliated_corporate_entity_id"])
                    if row["cataloged_affiliated_corporate_entity_id"] is not None
                    else None
                ),
                "catalog_unresolved_reason_code": (
                    row["catalog_unresolved_reason_code"] if catalog_node_id is None else None
                ),
                "affiliation_catalog_unresolved_reason_code": (
                    row["affiliation_catalog_unresolved_reason_code"]
                    if row["cataloged_affiliated_corporate_entity_id"] is None
                    else None
                ),
                **ontology_annotations(row["actor_type_code"]),
            }
        )
    return {
        "post_id": post_id,
        "korean_summary": header["korean_summary"],
        "summary_status": (
            "current" if summary_is_current else "stale"
        ),
        "summary_contract_version": summary_contract_version,
        "key_events": [row["event_text"] for row in events],
        "key_event_details": [
            {
                "event_text": row["event_text"],
                "project_name": row.get("project_name"),
                "evidence_text": row.get("evidence_text"),
            }
            for row in events
        ],
        "event_clues": [
            {
                "event_index": row["event_ordinal"],
                "clue_type_code": row["clue_type_code"],
                "clue_text": row["clue_text"],
                "target_text": row["target_text"],
                "normalized_value_text": row["normalized_value_text"],
                "assertion_code": row["assertion_code"],
                "evidence_text": row["evidence_text"],
                "ontology_iri": row["ontology_iri"],
                "extraction_method": row["extraction_method"],
            }
            for row in event_clues
        ],
        "roles_and_responsibilities": payload_roles,
        "major_event_actions": [
            {
                "action_text": row["action_text"],
                "requester_actor_name": row["requester_actor_name"],
                "processor_actor_name": row["processor_actor_name"],
                "evidence_text": row["evidence_text"],
                "project_name": row["project_name"],
            }
            for row in actions
        ],
        "quantitative_observations": [
            {
                "measurement_type_code": row["measurement_type_code"],
                "label_text": row["label_text"],
                "value_numeric": str(row["value_numeric"]),
                "unit_code": row["unit_code"],
                "quantity_numeric": (
                    str(row["quantity_numeric"])
                    if row["quantity_numeric"] is not None
                    else None
                ),
                "quantity_unit_code": row["quantity_unit_code"],
                "qualifier_text": row["qualifier_text"],
                "raw_value_text": row["raw_value_text"],
                "evidence_text": row["evidence_text"],
                "ontology_iri": row["ontology_iri"],
                "ontology_label": ontology_annotations(
                    row["measurement_type_code"]
                ).get("ontology_label"),
                "extraction_method": row["extraction_method"],
            }
            for row in quantitative_observations
        ],
        "source_grounded_facts": [
            {
                "fact_type_code": row["fact_type_code"],
                "label_text": row["label_text"],
                "value_text": row["value_text"],
                "normalized_value_text": row["normalized_value_text"],
                "assertion_code": row["assertion_code"],
                "normalized_date": (
                    row["normalized_date"].isoformat()
                    if row["normalized_date"] is not None
                    else None
                ),
                "date_precision_code": row["date_precision_code"],
                "normalization_evidence_text": row["normalization_evidence_text"],
                "qualifier_text": row["qualifier_text"],
                "evidence_text": row["evidence_text"],
                "ontology_iri": row["ontology_iri"],
                "ontology_label": ontology_annotations(row["fact_type_code"]).get(
                    "ontology_label"
                ),
                "extraction_method": row["extraction_method"],
            }
            for row in source_grounded_facts
        ],
        "semantic_relationships": [
            {
                "relation_ordinal": row["relation_ordinal"],
                "subject_name": row["subject_name"],
                "subject_type": row["subject_type"],
                "predicate_code": row["predicate_code"],
                "object_name": row["object_name"],
                "object_type": row["object_type"],
                "evidence_text": row["evidence_text"],
                "confidence": float(row["relation_confidence"]),
                "extraction_method": row["extraction_method"],
                **semantic_predicate_annotations(row["predicate_code"]),
            }
            for row in semantic_relationships
        ],
        "project_mentions": [
            {
                "project_key": row["project_key"],
                "project_name": row["project_name"],
                "evidence": row["evidence_text"],
                "confidence": float(row["mention_confidence"]),
                "ontology_iri": row["ontology_iri"],
                "extraction_method": row["extraction_method"],
            }
            for row in projects
        ],
    }


async def persist_post_summary(
    conn: asyncpg.Connection,
    post_id: str,
    summary: PostSummary,
    *,
    post_body: str,
    expected_source_body_sha256: str,
    require_image_evidence: bool = False,
    resolution_client: OrganizationNameResolutionClient | None = None,
    hierarchy_inference_client: CorporateHierarchyInferenceClient | None = None,
    verification_client: RelationVerificationClient | None = None,
) -> dict[str, Any]:
    """Replace the stored summary for ``post_id`` and return the public payload.

    ``post_body`` is the exact normalized summary input and the context an
    organization-actor hierarchy proposal is inferred from (ADR 0010). The
    pluggable clients default to unavailable Null
    clients, so an organization actor then only resolves against an existing
    ``corporate_entity``.

    Provider-only organization proposals are prepared before the
    exact-current source/evidence transaction. Catalog writes apply only after
    that recheck and share its transaction with summary replacement, so neither
    network latency nor stale provider output holds or mutates locked state
    (ADR 0114).
    """
    await require_summary_target(conn, post_id)
    normalized_summary_input = require_summary_source_body(post_body)
    summary_input_digest = summary_input_sha256(normalized_summary_input)

    hierarchy_inference_client = (
        hierarchy_inference_client or NullCorporateHierarchyInferenceClient()
    )
    resolution_client = resolution_client or NullOrganizationNameResolutionClient()
    verification_client = verification_client or NullRelationVerificationClient()

    context_text = normalized_summary_input
    candidates = (
        await _load_corporate_entity_candidates(conn)
        if summary.roles_and_responsibilities
        else []
    )
    prepared_organizations: dict[int, PreparedCorporateEntityResolution] = {}
    prepared_affiliations: dict[int, PreparedAffiliatedOrganization] = {}
    unavailable_affiliations: dict[int, tuple[str, str | None, str]] = {}
    for role_index, role in enumerate(summary.roles_and_responsibilities):
        if role.actor_type_code == ACTOR_TYPE_TEAM and is_generic_team_actor(
            role.actor_name
        ):
            continue
        if role.actor_type_code == ACTOR_TYPE_ORGANIZATION:
            prepared_organizations[role_index] = (
                await prepare_corporate_entity_resolution(
                    role.actor_name,
                    context_text,
                    hierarchy_inference_client,
                    verification_client,
                    candidates,
                )
            )
            continue
        if (
            role.actor_type_code in {ACTOR_TYPE_PERSON, ACTOR_TYPE_TEAM}
            and role.affiliated_organization_name
        ):
            try:
                prepared_affiliations[role_index] = (
                    await prepare_affiliated_organization(
                        conn,
                        role.affiliated_organization_name,
                        context_text,
                        resolution_client,
                        verification_client,
                        hierarchy_inference_client,
                        candidates,
                    )
                )
            except (HttpClientError, OSError, TimeoutError, ValueError):
                unavailable_affiliations[role_index] = (
                    role.affiliated_organization_name,
                    None,
                    "reason_no_live_client",
                )
    resolved_organization_ids: dict[int, str] = {}
    resolved_organization_reasons: dict[int, str] = {}
    resolved_affiliation_names: dict[int, str] = {}
    resolved_affiliation_ids: dict[int, str] = {}
    resolved_affiliation_reasons: dict[int, str] = {}

    async with conn.transaction():
        input_is_current = await _lock_current_summary_input(
            conn,
            post_id,
            expected_source_body_sha256=expected_source_body_sha256,
            expected_summary_input=normalized_summary_input,
            require_image_evidence=require_image_evidence,
        )
        if not input_is_current:
            raise RuntimeError("post summary input is no longer current")
        for role_index, role in enumerate(summary.roles_and_responsibilities):
            if role.actor_type_code == ACTOR_TYPE_TEAM and is_generic_team_actor(
                role.actor_name
            ):
                continue
            if role.actor_type_code != ACTOR_TYPE_ORGANIZATION:
                if (
                    role.actor_type_code in {ACTOR_TYPE_PERSON, ACTOR_TYPE_TEAM}
                    and role.affiliated_organization_name
                ):
                    prepared_affiliation = prepared_affiliations.get(role_index)
                    if prepared_affiliation is not None:
                        _, resolved_name, corporate_entity_id, affiliation_reason = (
                            await apply_prepared_affiliated_organization(
                                conn,
                                prepared_affiliation,
                                candidates,
                            )
                        )
                    else:
                        resolved_name, corporate_entity_id, affiliation_reason = (
                            unavailable_affiliations[role_index]
                        )
                    resolved_affiliation_names[role_index] = resolved_name
                    if corporate_entity_id is not None:
                        resolved_affiliation_ids[role_index] = corporate_entity_id
                    elif affiliation_reason is not None:
                        resolved_affiliation_reasons[role_index] = affiliation_reason
                continue
            corporate_entity_id, unresolved_reason = (
                await apply_prepared_corporate_entity_resolution(
                    conn,
                    prepared_organizations[role_index],
                    candidates,
                )
            )
            if corporate_entity_id is not None:
                resolved_organization_ids[role_index] = corporate_entity_id
            elif unresolved_reason is not None:
                resolved_organization_reasons[role_index] = unresolved_reason
        await _replace_summary_projection(
            conn,
            post_id,
            summary,
            candidates,
            resolved_organization_ids,
            resolved_affiliation_names,
            resolved_affiliation_ids,
            summary_input_digest,
            resolved_organization_reasons,
            resolved_affiliation_reasons,
        )
        payload = await fetch_persisted_summary(
            conn,
            post_id,
            summary_input=normalized_summary_input,
        )
        if payload is None:
            raise RuntimeError("persist_post_summary wrote no row")
        return payload


async def _resolve_existing_cataloged_person_id(
    conn: asyncpg.Connection, person_name: str
) -> tuple[str | None, str | None]:
    """Return ``(earliest existing catalog person id, unresolved reason)``.

    Lookup orders by ``created_at``, then ``person_id``. This function
    does not insert a ``cataloged_person`` row (ADR 0009). A missing
    catalog row stays unbound rather than inventing a person; ADR 0141
    records that absence as ``reason_no_catalog_entry`` -- the only reason
    code available here, since this lookup has no live-client dependency
    to distinguish further.
    """
    person_row = await conn.fetchrow(
        "select person_id from cataloged_person "
        "where person_name = $1 "
        "order by created_at, person_id limit 1",
        person_name,
    )
    if person_row is None:
        return None, "reason_no_catalog_entry"
    return str(person_row["person_id"]), None


async def _replace_summary_projection(
    conn: asyncpg.Connection,
    post_id: str,
    summary: PostSummary,
    candidates: list[Any],
    resolved_organization_ids: dict[int, str],
    resolved_affiliation_names: dict[int, str],
    resolved_affiliation_ids: dict[int, str],
    summary_input_digest: str,
    resolved_organization_reasons: dict[int, str] | None = None,
    resolved_affiliation_reasons: dict[int, str] | None = None,
) -> None:
    """Write one atomic replacement using pre-resolved shared identities."""
    # Summary replacement owns only R&R projections. Keyman mentions remain
    # independent and are combined only by the graph read/derivation view.
    await conn.execute(
        "delete from post_summary_person_mention where post_id = $1",
        post_id,
    )
    await conn.execute("delete from post_team_mention where post_id = $1", post_id)
    await conn.execute("delete from post_organization_mention where post_id = $1", post_id)
    await conn.execute("delete from post_summary_five_w1h where post_id = $1", post_id)
    await conn.execute(
        "delete from post_summary_quantitative_observation where post_id = $1", post_id
    )
    await conn.execute("delete from post_summary_source_fact where post_id = $1", post_id)
    await conn.execute(
        "delete from post_summary_semantic_relationship where post_id = $1", post_id
    )
    await conn.execute("delete from post_summary_event_clue where post_id = $1", post_id)
    await conn.execute("delete from post_summary_action where post_id = $1", post_id)
    await conn.execute("delete from post_summary_result where post_id = $1", post_id)
    await conn.execute("delete from post_project_mention where post_id = $1", post_id)
    await conn.execute(
        "insert into post_summary_result "
        "(post_id, korean_summary, summary_contract_version, summary_input_sha256) "
        "values ($1, $2, $3, $4)",
        post_id,
        summary.korean_summary,
        POST_SUMMARY_CONTRACT_VERSION,
        summary_input_digest,
    )
    for project in summary.project_mentions:
        project_key = normalize_project_key(project.canonical_name)
        if not project_key:
            continue
        await conn.execute(
            """
            insert into post_project_mention
                (post_id, project_key, project_name, evidence_text, mention_confidence,
                 ontology_iri, extraction_method)
            values ($1, $2, $3, $4, $5, $6, 'contextual_orchestrator_semantic')
            on conflict (post_id, project_key) do update set
                project_name = excluded.project_name,
                evidence_text = excluded.evidence_text,
                mention_confidence = excluded.mention_confidence,
                ontology_iri = excluded.ontology_iri,
                extraction_method = excluded.extraction_method
            """,
            post_id,
            project_key,
            project.project_name,
            project.evidence,
            project.confidence,
            str(LW.Project),
        )
    for ordinal, relation in enumerate(summary.semantic_relationships):
        await conn.execute(
            """
            insert into post_summary_semantic_relationship
                (post_id, relation_ordinal, subject_name, subject_type,
                 predicate_code, object_name, object_type, evidence_text,
                 relation_confidence)
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            post_id,
            ordinal,
            relation.subject_name,
            relation.subject_type,
            relation.predicate_code,
            relation.object_name,
            relation.object_type,
            relation.evidence_text,
            relation.confidence,
        )
    event_details = summary.key_event_details or tuple(
        KeyEvent(event_text=event_text) for event_text in summary.key_events
    )
    project_keys = {
        normalize_project_key(project.canonical_name)
        for project in summary.project_mentions
        if normalize_project_key(project.canonical_name)
    }
    for ordinal, event in enumerate(event_details):
        normalized_event_project_key = (
            normalize_project_key(event.project_key) if event.project_key else None
        )
        project_key = (
            normalized_event_project_key
            if normalized_event_project_key in project_keys
            else None
        )
        await conn.execute(
            "insert into post_summary_event "
            "(post_id, event_ordinal, event_text, evidence_text, project_key, ontology_iri, extraction_method) "
            "values ($1, $2, $3, $4, $5, $6, $7)",
            post_id,
            ordinal,
            event.event_text,
            event.evidence_text,
            project_key,
            str(LW.KeyEvent),
            "contextual_orchestrator_event",
        )
    for clue_ordinal, clue in enumerate(summary.event_clues):
        if clue.event_index >= len(event_details):
            continue
        await conn.execute(
            """
            insert into post_summary_event_clue
                (post_id, event_ordinal, clue_ordinal, clue_type_code, clue_text,
                 target_text, normalized_value_text, assertion_code, evidence_text,
                 ontology_iri, extraction_method)
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            post_id,
            clue.event_index,
            clue_ordinal,
            clue.clue_type_code,
            clue.clue_text,
            clue.target_text,
            clue.normalized_value_text,
            clue.assertion_code,
            clue.evidence_text,
            str(LW.EvidenceClue),
            "contextual_orchestrator_event_clue",
        )
    for ordinal, claim in enumerate(summary.five_w1h_evidence):
        await conn.execute(
            "insert into post_summary_five_w1h "
            "(post_id, slot_code, value_ordinal, value_text, evidence_text) "
            "values ($1, $2, $3, $4, $5)",
            post_id,
            claim.slot_code,
            ordinal,
            claim.value_text,
            claim.evidence_text,
        )
    for ordinal, observation in enumerate(summary.quantitative_observations):
        await conn.execute(
            """
            insert into post_summary_quantitative_observation
                (post_id, observation_ordinal, measurement_type_code, label_text,
                 value_numeric, unit_code, quantity_numeric, quantity_unit_code,
                 qualifier_text, raw_value_text, evidence_text, ontology_iri,
                 extraction_method)
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
            post_id,
            ordinal,
            observation.measurement_type_code,
            observation.label_text,
            observation.value_numeric,
            observation.unit_code,
            observation.quantity_numeric,
            observation.quantity_unit_code,
            observation.qualifier_text,
            observation.raw_value_text,
            observation.evidence_text,
            str(LW.QuantitativeObservation),
            "contextual_orchestrator_quantitative",
        )
    for ordinal, fact in enumerate(summary.source_grounded_facts):
        await conn.execute(
            """
            insert into post_summary_source_fact
                (post_id, fact_ordinal, fact_type_code, label_text, value_text,
                 normalized_value_text, assertion_code, normalized_date,
                 date_precision_code, normalization_evidence_text, qualifier_text,
                 evidence_text, ontology_iri, extraction_method)
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            post_id,
            ordinal,
            fact.fact_type_code,
            fact.label_text,
            fact.value_text,
            fact.normalized_value_text,
            fact.assertion_code,
            fact.normalized_date,
            fact.date_precision_code,
            fact.normalization_evidence_text,
            fact.qualifier_text,
            fact.evidence_text,
            str(LW.SourceGroundedFact),
            "contextual_orchestrator_source_fact",
        )
    # ADR 0009 / 0019 / 0027: resolve catalog identity before writing
    # the role row so fetch never reconstructs it by a non-unique name.
    for role_index, role in enumerate(summary.roles_and_responsibilities):
        if role.actor_type_code == ACTOR_TYPE_TEAM and is_generic_team_actor(role.actor_name):
            continue
        cataloged_team_id = None
        cataloged_corporate_entity_id = None
        cataloged_person_id = None
        catalog_unresolved_reason_code = None
        cataloged_affiliated_corporate_entity_id = resolved_affiliation_ids.get(role_index)
        affiliation_catalog_unresolved_reason_code = (
            None
            if cataloged_affiliated_corporate_entity_id is not None
            else (resolved_affiliation_reasons or {}).get(role_index)
        )
        affiliation_name = resolved_affiliation_names.get(
            role_index, role.affiliated_organization_name
        )
        if role.actor_type_code == ACTOR_TYPE_TEAM:
            cataloged_team_id = await upsert_team(
                conn,
                role.actor_name,
                affiliation_name,
                candidates,
            )
        elif role.actor_type_code == ACTOR_TYPE_ORGANIZATION:
            cataloged_corporate_entity_id = resolved_organization_ids.get(
                role_index
            )
            if cataloged_corporate_entity_id is None:
                catalog_unresolved_reason_code = (resolved_organization_reasons or {}).get(
                    role_index
                )
        elif role.actor_type_code == ACTOR_TYPE_PERSON:
            cataloged_person_id, catalog_unresolved_reason_code = (
                await _resolve_existing_cataloged_person_id(
                    conn,
                    role.actor_name,
                )
            )
        await conn.execute(
            "insert into post_summary_role "
            "(post_id, actor_name, responsibility_text, actor_type_code, "
            "affiliated_organization_name, cataloged_team_id, "
            "cataloged_corporate_entity_id, cataloged_person_id, "
            "cataloged_affiliated_corporate_entity_id, "
            "catalog_unresolved_reason_code, "
            "affiliation_catalog_unresolved_reason_code) values "
            "($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
            post_id,
            role.actor_name,
            role.responsibility,
            role.actor_type_code,
            role.affiliated_organization_name,
            cataloged_team_id,
            cataloged_corporate_entity_id,
            cataloged_person_id,
            cataloged_affiliated_corporate_entity_id,
            catalog_unresolved_reason_code,
            affiliation_catalog_unresolved_reason_code,
        )
        if cataloged_team_id is not None:
            await conn.execute(
                "insert into post_team_mention (post_id, team_id) values ($1, $2) "
                "on conflict do nothing",
                post_id,
                cataloged_team_id,
            )
        organization_ids = []
        if cataloged_corporate_entity_id is not None:
            organization_ids.append(cataloged_corporate_entity_id)
        if cataloged_affiliated_corporate_entity_id is not None:
            organization_ids.append(cataloged_affiliated_corporate_entity_id)
        for organization_id in dict.fromkeys(organization_ids):
            await conn.execute(
                "insert into post_organization_mention "
                "(post_id, corporate_entity_id) values ($1, $2) "
                "on conflict do nothing",
                post_id,
                organization_id,
            )
        if cataloged_person_id is not None:
            await conn.execute(
                "insert into post_summary_person_mention (post_id, person_id) "
                "values ($1, $2) on conflict do nothing",
                post_id,
                cataloged_person_id,
            )
    role_names = {
        role.actor_name
        for role in summary.roles_and_responsibilities
        if not (role.actor_type_code == ACTOR_TYPE_TEAM and is_generic_team_actor(role.actor_name))
    }
    project_keys = {
        normalize_project_key(project.canonical_name)
        for project in summary.project_mentions
        if normalize_project_key(project.canonical_name)
    }
    for ordinal, action in enumerate(summary.major_event_actions):
        actor_names = (action.requester_actor_name, action.processor_actor_name)
        if any(name is not None and name not in role_names for name in actor_names):
            continue
        normalized_action_project_key = (
            normalize_project_key(action.project_key) if action.project_key else None
        )
        project_key = (
            normalized_action_project_key
            if normalized_action_project_key in project_keys
            else None
        )
        await conn.execute(
            """
            insert into post_summary_action
                (post_id, action_ordinal, action_text, requester_actor_name,
                 processor_actor_name, evidence_text, project_key)
            values ($1, $2, $3, $4, $5, $6, $7)
            """,
            post_id,
            ordinal,
            action.action_text,
            action.requester_actor_name,
            action.processor_actor_name,
            action.evidence_text,
            project_key,
        )
    await persist_edges_for_post(conn, post_id)


def seeded_demo_summary() -> PostSummary:
    """Synthetic Korean summary for the demo public post -- not an LLM result."""
    return PostSummary(
        korean_summary=(
            "에이다 웨스트가 데모 코프를 대표해 노스리지 그리드의 프리야 네어에게 "
            "지연된 출하 일정을 확인했다."
        ),
        key_events=("출하 지연 후속 연락",),
        roles_and_responsibilities=(
            RoleResponsibility(
                actor_name="Ada West",
                responsibility="일정 확인 후속",
                affiliated_organization_name="Demo Corp",
            ),
            RoleResponsibility(
                actor_name="Priya Nair",
                responsibility="고객 측 수신",
                affiliated_organization_name="Northridge Grid",
            ),
            RoleResponsibility(
                actor_name="당사",
                responsibility="출하 일정 확정",
                actor_type_code=ACTOR_TYPE_ORGANIZATION,
            ),
        ),
    )


def seeded_fixture_summary(post_title: str) -> PostSummary | None:
    """Synthetic Korean summary for a reconstruct/calendar fixture title.

    Not an LLM result. Returns None when the title is not a known seed
    fixture so a missing row still 503s instead of inventing prose.
    R&R names come from ``fixture_thread_cast`` -- rec-006 and the
    calendar commitment stay empty because they have no cast people.
    """
    summary = _FIXTURE_SUMMARIES.get(post_title)
    if summary is None:
        return None
    roles = _roles_for_fixture(post_title)
    if not roles:
        return summary
    return PostSummary(
        korean_summary=summary.korean_summary,
        key_events=summary.key_events,
        roles_and_responsibilities=roles,
    )


def _roles_for_fixture(post_title: str) -> tuple[RoleResponsibility, ...]:
    """Title-derived R&R for the fixture cast -- not an LLM judge."""
    cast = fixture_thread_cast(post_title)
    if cast is None or not cast.person_names:
        return ()
    return tuple(
        RoleResponsibility(
            actor_name=name,
            responsibility=responsibility,
            affiliated_organization_name=_FIXTURE_ROLE_AFFILIATION.get(name),
        )
        for name in cast.person_names
        if (responsibility := _FIXTURE_ROLE_RESPONSIBILITY.get(name))
    )


_FIXTURE_ROLE_RESPONSIBILITY = {
    "Ada West": "우리 측 후속",
    "Priya Nair": "고객 측 수신",
    "Jordan Hale": "사양 검토",
}

_FIXTURE_ROLE_AFFILIATION = {
    "Ada West": "Demo Corp",
    "Priya Nair": "Northridge Grid",
    "Jordan Hale": "Westfield Power",
}


def _summary(korean: str, *events: str) -> PostSummary:
    """Create one compact synthetic fixture summary."""
    return PostSummary(korean_summary=korean, key_events=events)


_FIXTURE_SUMMARIES: dict[str, PostSummary] = {
    "Initial site visit and project scope discussion": _summary(
        "착수 전에 현장을 둘러보고 이번 일의 작업 범위를 맞추는 회의가 열렸다.",
        "초기 현장 방문",
        "프로젝트 범위 논의",
    ),
    "Pricing renegotiation follow-up": _summary(
        "초기 방문 이후 가격 재협상을 이어가는 후속 협의가 열렸다.",
        "가격 재협상 후속",
    ),
    "Pricing renegotiation: revised quote sent": _summary(
        "재협상 결과를 반영한 수정 견적이 상대에게 발송되었다.",
        "수정 견적 발송",
    ),
    "Delivery schedule question raised": _summary(
        "가격 논의와 별도로 납품 일정에 대한 질문이 올라왔다.",
        "납품 일정 질의",
    ),
    "Delivery schedule confirmed with logistics": _summary(
        "물류 담당과 확인한 뒤 납품 일정이 확정되었다.",
        "물류 확인",
        "납품 일정 확정",
    ),
    "Unrelated: annual account review": _summary(
        "연례 계정 검토가 진행되었다. 가격 재협상이나 납품 일정과는 주제가 다르다.",
        "연례 계정 검토",
    ),
    "Technical specification review meeting": _summary(
        "기술 사양을 점검하는 검토 회의가 열렸다.",
        "기술 사양 검토 회의",
    ),
    "Specification revision requested": _summary(
        "검토 결과에 따라 사양 수정이 요청되었다.",
        "사양 수정 요청",
    ),
    "Revised specification approved": _summary(
        "수정된 기술 사양이 승인되어 후속 작업 기준이 정해졌다.",
        "수정 사양 승인",
    ),
    "Follow-up on the Riverbend order confirmation": _summary(
        "리버벤드 주문은 이미 확인됐고, 수정 납품 일정을 다음 금요일까지 보내기로 했다.",
        "주문 확인 완료",
        "납품 일정 약속",
    ),
}
