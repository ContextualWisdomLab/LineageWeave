"""Persist evidence-bearing additional Voice assignments (ADR 0251)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

from lineageweave.knowledge_graph import NODE_POST
from lineageweave.ontology import LW, ontology_node_iri


class PrimaryVoiceAssignmentError(ValueError):
    """Raised when the additional-voice path targets the imported primary."""


async def _post_resource_id(conn: asyncpg.Connection, post_id: str) -> str:
    """Return the bound PROV Entity resource for one evidence post."""
    existing = await conn.fetchval(
        """
        select resource_id
          from provenance_resource_binding
         where node_type_code = 'node_post'
           and node_id = $1::uuid
        """,
        post_id,
    )
    if existing is not None:
        await conn.execute(
            """
            insert into provenance_resource_type (resource_id, class_code)
            values ($1::uuid, 'prov_entity')
            on conflict do nothing
            """,
            existing,
        )
        return str(existing)
    resource_id = await conn.fetchval(
        """
        insert into provenance_resource (resource_iri, resource_label)
        values ($1, 'Authorized Voice evidence post')
        on conflict (resource_iri) do update
        set resource_label = coalesce(
            provenance_resource.resource_label,
            excluded.resource_label
        )
        returning resource_id
        """,
        ontology_node_iri(NODE_POST, post_id),
    )
    await conn.execute(
        """
        insert into provenance_resource_type (resource_id, class_code)
        values ($1::uuid, 'prov_entity')
        on conflict do nothing
        """,
        resource_id,
    )
    await conn.execute(
        """
        insert into provenance_resource_binding (resource_id, node_type_code, node_id)
        values ($1::uuid, 'node_post', $2::uuid)
        on conflict do nothing
        """,
        resource_id,
        post_id,
    )
    bound = await conn.fetchval(
        """
        select resource_id
          from provenance_resource_binding
         where node_type_code = 'node_post'
           and node_id = $1::uuid
        """,
        post_id,
    )
    if bound is None:
        raise RuntimeError("evidence post provenance binding was not persisted")
    return str(bound)


async def persist_additional_voice_assignment(
    conn: asyncpg.Connection,
    *,
    post_id: str,
    voice_type_code: str,
    truth_status_code: str,
    evidence_post_id: str,
) -> None:
    """Atomically bind one additional Voice to an authorized evidence post."""
    assignment_iri = str(LW[f"voice-assignment/{post_id}/{voice_type_code}"])
    async with conn.transaction():
        evidence_resource_id = await _post_resource_id(conn, evidence_post_id)
        assignment_resource_id = await conn.fetchval(
            """
            insert into provenance_resource (resource_iri, resource_label)
            values ($1, 'Qualified Voice assignment')
            on conflict (resource_iri) do update
            set resource_label = coalesce(
                provenance_resource.resource_label,
                excluded.resource_label
            )
            returning resource_id
            """,
            assignment_iri,
        )
        await conn.execute(
            """
            insert into provenance_resource_type (resource_id, class_code)
            values ($1::uuid, 'prov_entity')
            on conflict do nothing
            """,
            assignment_resource_id,
        )
        assertion_id = await conn.fetchval(
            """
            insert into provenance_assertion
                (subject_resource_id, relation_code, object_resource_id)
            values ($1::uuid, 'prov_was_derived_from', $2::uuid)
            on conflict do nothing
            returning assertion_id
            """,
            assignment_resource_id,
            evidence_resource_id,
        )
        if assertion_id is None:
            assertion_id = await conn.fetchval(
                """
                select assertion_id
                  from provenance_assertion
                 where subject_resource_id = $1::uuid
                   and relation_code = 'prov_was_derived_from'
                   and object_resource_id = $2::uuid
                   and bundle_resource_id is null
                """,
                assignment_resource_id,
                evidence_resource_id,
            )
        if assertion_id is None:
            raise RuntimeError("Voice evidence derivation was not persisted")
        stored = await conn.fetchrow(
            """
            insert into source_post_voice
                (post_id, voice_type_code, is_primary, truth_status_code,
                 provenance_assertion_id, effective_from, recorded_at)
            values ($1::uuid, $2, false, $3, $4::uuid, now(), now())
            on conflict (post_id, voice_type_code) do update
            set truth_status_code = excluded.truth_status_code,
                provenance_assertion_id = excluded.provenance_assertion_id,
                recorded_at = now()
            where not source_post_voice.is_primary
            returning voice_type_code
            """,
            post_id,
            voice_type_code,
            truth_status_code,
            assertion_id,
        )
        if stored is None:
            raise PrimaryVoiceAssignmentError(
                "the imported primary Voice cannot be changed through the additional-voice path"
            )


__all__ = ["PrimaryVoiceAssignmentError", "persist_additional_voice_assignment"]
