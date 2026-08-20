"""Atomic writer for source-owned project lifecycle evidence.

The writer is an administrative/import boundary.  It accepts explicit source
codes and evidence posts, never classifies a title or body, and replaces only
the source-system record that owns the projection.
"""

from __future__ import annotations

import json
from typing import Any
from unicodedata import normalize

import asyncpg

from lineageweave.project_lifecycle import (
    PROJECT_EVENT_TYPE_CODES,
    ProjectLifecycleEventInput,
    ProjectLifecycleValidationError,
    project_lifecycle_digest,
    require_project_lifecycle_write_permission,
    validate_project_lifecycle_event,
)


def _text(value: str) -> str:
    """Normalize a validated identifier before binding it to SQL."""

    return normalize("NFKC", value).strip()


async def _assert_evidence_post(
    conn: asyncpg.Connection,
    evidence_post_id: str,
    source_system_code: str,
    source_record_key: str,
) -> None:
    """Require evidence to belong to the same source record as the import."""

    row = await conn.fetchrow(
        """
        select post_id
          from source_post
         where post_id = $1::uuid
           and source_system_code = $2
           and source_record_key = $3
        """,
        evidence_post_id,
        source_system_code,
        source_record_key,
    )
    if row is None:
        raise ProjectLifecycleValidationError(
            "evidence post must belong to the imported source system and record"
        )


async def _mapping_row(
    conn: asyncpg.Connection, event: ProjectLifecycleEventInput
) -> asyncpg.Record:
    """Resolve the active, versioned external code mapping or fail closed."""

    row = await conn.fetchrow(
        """
        select mapping.project_event_mapping_id as mapping_id,
               mapping.project_source_system_id as source_system_id,
               mapping.project_event_type_code
          from project_event_mapping mapping
          join project_source_system source_system
            on source_system.project_source_system_id = mapping.project_source_system_id
         where source_system.source_system_code = $1
           and mapping.mapping_version = $2
           and mapping.source_event_code = $3
           and mapping.is_active
        """,
        _text(event.source_system_code),
        _text(event.mapping_version),
        _text(event.source_event_code),
    )
    if row is None:
        raise ProjectLifecycleValidationError(
            "no active project event mapping exists for the source code and version"
        )
    if row["project_event_type_code"] not in PROJECT_EVENT_TYPE_CODES:
        raise ProjectLifecycleValidationError("mapping resolves to an unregistered project event type")
    return row


async def register_project_event_mapping(
    conn: asyncpg.Connection,
    *,
    source_system_code: str,
    source_system_name: str,
    mapping_version: str,
    source_event_code: str,
    project_event_type_code: str,
    administrator_key: str,
    permission_codes: set[str],
) -> dict[str, str]:
    """Register or activate one explicit source-system event mapping.

    This is the administrative mapping adapter.  It is intentionally separate
    from lifecycle ingestion so unknown source codes cannot become events by
    accident.
    """

    require_project_lifecycle_write_permission(permission_codes)
    if not administrator_key.strip():
        raise PermissionError("administrator_key is required")
    values = {
        "source_system_code": _text(source_system_code),
        "source_system_name": _text(source_system_name),
        "mapping_version": _text(mapping_version),
        "source_event_code": _text(source_event_code),
    }
    if any(not value for value in values.values()):
        raise ProjectLifecycleValidationError("mapping fields must be non-empty")
    if project_event_type_code not in PROJECT_EVENT_TYPE_CODES:
        raise ProjectLifecycleValidationError(
            f"unsupported project_event_type_code: {project_event_type_code!r}"
        )
    async with conn.transaction():
        system_id = await conn.fetchval(
            """
            insert into project_source_system (source_system_code, source_system_name)
            values ($1, $2)
            on conflict (source_system_code) do update
                set source_system_name = excluded.source_system_name
            returning project_source_system_id
            """,
            values["source_system_code"],
            values["source_system_name"],
        )
        mapping_id = await conn.fetchval(
            """
            insert into project_event_mapping
                (project_source_system_id, mapping_version, source_event_code,
                 project_event_type_code, is_active)
            values ($1, $2, $3, $4, true)
            on conflict (project_source_system_id, mapping_version, source_event_code) do update
                set project_event_type_code = excluded.project_event_type_code,
                    is_active = true
            returning project_event_mapping_id
            """,
            system_id,
            values["mapping_version"],
            values["source_event_code"],
            project_event_type_code,
        )
    return {"project_event_mapping_id": str(mapping_id), "status_code": "registered"}


async def _upsert_project_identity(
    conn: asyncpg.Connection, project_key: str, project_name: str
) -> str:
    """Create or update the normalized project display identity."""

    return str(
        await conn.fetchval(
            """
            insert into project_identity (project_key, project_name)
            values ($1, $2)
            on conflict (project_key) do update
                set project_name = excluded.project_name
            returning project_identity_id
            """,
            project_key,
            _text(project_name),
        )
    )


async def ingest_project_lifecycle_event(
    conn: asyncpg.Connection,
    event: ProjectLifecycleEventInput,
    *,
    administrator_key: str,
    permission_codes: set[str],
) -> dict[str, Any]:
    """Atomically insert or replace one source-owned lifecycle projection.

    Repeating the same source identity is idempotent.  Replacing it deletes and
    recreates only its owned relations and responsibility rows; independent
    source records remain untouched.  The returned data is aggregate identity
    and status, not source content.
    """

    require_project_lifecycle_write_permission(permission_codes)
    if not administrator_key.strip():
        raise PermissionError("administrator_key is required")
    project_key = validate_project_lifecycle_event(event)
    digest = project_lifecycle_digest(event)

    async with conn.transaction():
        lock_key = json.dumps(
            [_text(event.source_system_code), _text(event.source_record_key)],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        await conn.execute("select pg_advisory_xact_lock(hashtextextended($1, 0))", lock_key)
        mapping = await _mapping_row(conn, event)
        await _assert_evidence_post(
            conn,
            event.evidence_post_id,
            _text(event.source_system_code),
            _text(event.source_record_key),
        )
        for relation in event.relations:
            await _assert_evidence_post(
                conn,
                relation.evidence_post_id,
                _text(event.source_system_code),
                _text(event.source_record_key),
            )
        for responsibility in event.responsibilities:
            await _assert_evidence_post(
                conn,
                responsibility.evidence_post_id,
                _text(event.source_system_code),
                _text(event.source_record_key),
            )

        previous = await conn.fetchrow(
            """
            select project_source_record_id, record_digest
              from project_source_record
             where project_source_system_id = $1
               and source_record_key = $2
             for update
            """,
            mapping["source_system_id"],
            _text(event.source_record_key),
        )
        identity_id = await _upsert_project_identity(conn, project_key, event.project_name)
        source_record_id = await conn.fetchval(
            """
            insert into project_source_record
                (project_source_system_id, source_record_key, project_identity_id,
                 project_event_mapping_id, lifecycle_state_code, record_digest,
                 imported_by)
            values ($1, $2, $3, $4, 'project_record_active', $5, $6)
            on conflict (project_source_system_id, source_record_key) do update set
                project_identity_id = excluded.project_identity_id,
                project_event_mapping_id = excluded.project_event_mapping_id,
                lifecycle_state_code = excluded.lifecycle_state_code,
                record_digest = excluded.record_digest,
                imported_by = excluded.imported_by,
                imported_at = now()
            returning project_source_record_id
            """,
            mapping["source_system_id"],
            _text(event.source_record_key),
            identity_id,
            mapping["mapping_id"],
            digest,
            administrator_key.strip(),
        )
        project_event_id = await conn.fetchval(
            """
            insert into project_lifecycle_event
                (project_source_record_id, project_event_type_code,
                 event_started_at, event_ended_at, event_digest)
            values ($1, $2, $3, $4, $5)
            on conflict (project_source_record_id) do update set
                project_event_type_code = excluded.project_event_type_code,
                event_started_at = excluded.event_started_at,
                event_ended_at = excluded.event_ended_at,
                event_digest = excluded.event_digest
            returning project_lifecycle_event_id
            """,
            source_record_id,
            mapping["project_event_type_code"],
            event.event_started_at,
            event.event_ended_at,
            digest,
        )
        await conn.execute(
            "delete from project_event_evidence where project_lifecycle_event_id = $1",
            project_event_id,
        )
        await conn.execute(
            """
            insert into project_event_evidence
                (project_lifecycle_event_id, evidence_post_id, evidence_role_code)
            values ($1, $2::uuid, 'project_event_primary_evidence')
            """,
            project_event_id,
            event.evidence_post_id,
        )
        await conn.execute(
            "delete from project_event_relation where owner_source_record_id = $1",
            source_record_id,
        )
        await conn.execute(
            "delete from project_event_responsibility where owner_source_record_id = $1",
            source_record_id,
        )
        for relation in event.relations:
            target = await conn.fetchrow(
                """
                select target_event.project_lifecycle_event_id, target_record.project_identity_id
                  from project_source_record target_record
                  join project_lifecycle_event target_event
                    on target_event.project_source_record_id = target_record.project_source_record_id
                join project_source_system target_system
                  on target_system.project_source_system_id = target_record.project_source_system_id
                 where target_system.source_system_code = $1
                   and target_record.source_record_key = $2
                   and target_record.lifecycle_state_code = 'project_record_active'
                """,
                _text(relation.target_source_system_code),
                _text(relation.target_source_record_key),
            )
            if target is None or str(target["project_identity_id"]) != str(identity_id):
                raise ProjectLifecycleValidationError(
                    "relation target must be an active event in the same project"
                )
            await conn.execute(
                """
                insert into project_event_relation
                    (owner_source_record_id, source_lifecycle_event_id,
                     target_lifecycle_event_id, relation_type_code, evidence_post_id)
                values ($1, $2, $3, $4, $5::uuid)
                """,
                source_record_id,
                project_event_id,
                target["project_lifecycle_event_id"],
                relation.relation_type_code,
                relation.evidence_post_id,
            )
        for responsibility in event.responsibilities:
            actor_id = await conn.fetchval(
                """
                insert into project_actor
                    (project_identity_id, actor_type_code, actor_key, actor_name)
                values ($1, $2, $3, $4)
                on conflict (project_identity_id, actor_type_code, actor_key) do update
                    set actor_name = excluded.actor_name
                returning project_actor_id
                """,
                identity_id,
                responsibility.actor_type_code,
                _text(responsibility.actor_key),
                _text(responsibility.actor_name),
            )
            await conn.execute(
                """
                insert into project_event_responsibility
                    (owner_source_record_id, project_lifecycle_event_id,
                     project_actor_id, responsibility_text, evidence_post_id)
                values ($1, $2, $3, $4, $5::uuid)
                """,
                source_record_id,
                project_event_id,
                actor_id,
                _text(responsibility.responsibility_text),
                responsibility.evidence_post_id,
            )
        await conn.execute(
            """
            insert into project_lifecycle_audit
                (project_source_record_id, action_code, actor_key,
                 mapping_version, before_digest, after_digest)
            values ($1, 'project_lifecycle_upserted', $2, $3, $4, $5)
            """,
            source_record_id,
            _text(administrator_key),
            _text(event.mapping_version),
            previous["record_digest"] if previous else None,
            digest,
        )
    return {
        "status_code": "replaced" if previous else "inserted",
        "project_source_record_id": str(source_record_id),
        "project_lifecycle_event_id": str(project_event_id),
        "record_digest": digest,
    }


async def withdraw_project_lifecycle_record(
    conn: asyncpg.Connection,
    *,
    source_system_code: str,
    source_record_key: str,
    administrator_key: str,
    permission_codes: set[str],
) -> dict[str, Any]:
    """Withdraw one source channel while preserving independent source rows."""

    require_project_lifecycle_write_permission(permission_codes)
    if not administrator_key.strip():
        raise PermissionError("administrator_key is required")
    if not source_system_code.strip() or not source_record_key.strip():
        raise ProjectLifecycleValidationError("source identity must be non-empty")

    async with conn.transaction():
        await conn.execute(
            "select pg_advisory_xact_lock(hashtextextended($1, 0))",
            json.dumps(
                [_text(source_system_code), _text(source_record_key)],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
        row = await conn.fetchrow(
            """
            select record.project_source_record_id, record.record_digest,
                   mapping.mapping_version, lifecycle.project_lifecycle_event_id
              from project_source_record record
              join project_source_system source_system
                on source_system.project_source_system_id = record.project_source_system_id
              join project_event_mapping mapping
                on mapping.project_event_mapping_id = record.project_event_mapping_id
              left join project_lifecycle_event lifecycle
                on lifecycle.project_source_record_id = record.project_source_record_id
             where source_system.source_system_code = $1
               and record.source_record_key = $2
             for update of record
            """,
            _text(source_system_code),
            _text(source_record_key),
        )
        if row is None:
            return {"status_code": "not_found"}
        if row["project_lifecycle_event_id"] is not None:
            await conn.execute(
                """
                delete from project_event_relation
                 where source_lifecycle_event_id = $1
                    or target_lifecycle_event_id = $1
                """,
                row["project_lifecycle_event_id"],
            )
            await conn.execute(
                "delete from project_event_responsibility where owner_source_record_id = $1",
                row["project_source_record_id"],
            )
            await conn.execute(
                "delete from project_lifecycle_event where project_lifecycle_event_id = $1",
                row["project_lifecycle_event_id"],
            )
        await conn.execute(
            """
            update project_source_record
               set lifecycle_state_code = 'project_record_withdrawn',
                   imported_by = $2,
                   imported_at = now()
             where project_source_record_id = $1
            """,
            row["project_source_record_id"],
            _text(administrator_key),
        )
        await conn.execute(
            """
            insert into project_lifecycle_audit
                (project_source_record_id, action_code, actor_key,
                 mapping_version, before_digest, after_digest)
            values ($1, 'project_lifecycle_withdrawn', $2, $3, $4, null)
            """,
            row["project_source_record_id"],
            _text(administrator_key),
            row["mapping_version"],
            row["record_digest"],
        )
    return {
        "status_code": "withdrawn",
        "project_source_record_id": str(row["project_source_record_id"]),
    }


__all__ = [
    "ingest_project_lifecycle_event",
    "register_project_event_mapping",
    "withdraw_project_lifecycle_record",
]
