"""Atomic analysis-run write: snapshot reuse, run, scope, first pending event.

ADR 0013 follow-up 1 / ADR 0017. This module creates a lineage request
against an already-captured snapshot. It does not invent a TEPP theta,
create a local psychometric substitute, or persist source SQL, DSNs,
raw posts, or provider bodies.

Idempotency is account-scoped. A retry with the same key and the same
request digest returns the existing run. A retry that names different
evidence or configuration is a conflict.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
from asyncpg.exceptions import UniqueViolationError

from lineageweave import __version__ as PACKAGE_VERSION

LINEAGE_RUN_KIND = "analysis_run_lineage"
TEPP_RUN_KIND = "analysis_run_tepp"
REPORT_RUN_KIND = "analysis_run_report"
CORPORATE_SCOPE_KIND = "analysis_scope_corporate_entity"
PENDING_STATUS = "analysis_status_pending"
LINEAGE_SCHEMA_VERSION = "lineage-run-v1"
_IDEMPOTENCY_KEY = re.compile(r"^[^\x00-\x1f]{1,256}$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class AnalysisRunWriteError(Exception):
    """Base class for fail-closed write outcomes the API can map."""


class AnalysisRunNotAllowed(AnalysisRunWriteError):
    """The requested kind is not created by this endpoint."""


class AnalysisRunForbiddenScope(AnalysisRunWriteError):
    """The caller asked for a corporate entity they may not walk."""


class AnalysisRunSnapshotMissing(AnalysisRunWriteError):
    """No captured snapshot is bound to this corporate entity yet."""


class AnalysisRunConflict(AnalysisRunWriteError):
    """The same account/key already names a different reconstruction."""

    def __init__(self, analysis_run_id: str) -> None:
        super().__init__("idempotency key already names a different reconstruction")
        self.analysis_run_id = analysis_run_id


class AnalysisRunInvalidRequest(AnalysisRunWriteError):
    """The request key, cutoff, or identifier is not canonical."""


@dataclass(frozen=True)
class AnalysisRunWriteResult:
    """One created or replayed pending lineage run."""

    analysis_run_id: str
    replayed: bool


def canonical_idempotency_key(raw: str) -> str:
    """Trim and accept a control-free 1..256 character client key.

    The database also enforces ``btrim`` plus no control characters.
    Rejecting here keeps the HTTP 422 distinct from a constraint 500.
    """
    if not isinstance(raw, str):
        raise AnalysisRunInvalidRequest("idempotency_key must be a string")
    key = raw.strip()
    if not key or len(key) > 256 or not _IDEMPOTENCY_KEY.match(key):
        raise AnalysisRunInvalidRequest(
            "idempotency_key must be 1..256 trimmed characters without controls"
        )
    return key


def parse_knowledge_cutoff(raw: str | None, *, requested_at: datetime) -> datetime:
    """Parse an optional ISO-8601 cutoff and keep it on or before request time."""
    if raw is None or raw == "":
        return requested_at
    try:
        cutoff = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AnalysisRunInvalidRequest(
            "knowledge_cutoff must be an ISO-8601 timestamp"
        ) from exc
    if cutoff.tzinfo is None:
        raise AnalysisRunInvalidRequest("knowledge_cutoff must include a timezone")
    cutoff = cutoff.astimezone(timezone.utc)
    if cutoff > requested_at:
        raise AnalysisRunInvalidRequest(
            "knowledge_cutoff cannot be later than the request time"
        )
    return cutoff


def request_configuration_digest(
    *,
    run_kind_code: str,
    scope_kind_code: str,
    corporate_entity_id: str,
    snapshot_sha256: str,
    knowledge_cutoff: datetime,
    configuration_schema_version: str,
) -> str:
    """SHA-256 of the canonical request the idempotency retry must match."""
    payload = {
        "configuration_schema_version": configuration_schema_version,
        "corporate_entity_id": corporate_entity_id,
        "knowledge_cutoff": knowledge_cutoff.isoformat().replace("+00:00", "Z"),
        "run_kind_code": run_kind_code,
        "scope_kind_code": scope_kind_code,
        "snapshot_sha256": snapshot_sha256,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def code_revision_digest() -> str:
    """64-hex digest of this package version -- never a source row."""
    return hashlib.sha256(f"lineageweave-{PACKAGE_VERSION}".encode("utf-8")).hexdigest()


def _require_lineage_kind(run_kind_code: str) -> None:
    """Reject TEPP and report writes so this slice cannot fake those products."""
    if run_kind_code == TEPP_RUN_KIND:
        raise AnalysisRunNotAllowed(
            "Connect a TEPP transport from a Failed TEPP row; this endpoint "
            "does not invent a measurement."
        )
    if run_kind_code == REPORT_RUN_KIND:
        raise AnalysisRunNotAllowed(
            "Rebuild the period report from the Reports panel."
        )
    if run_kind_code != LINEAGE_RUN_KIND:
        raise AnalysisRunNotAllowed(
            "Only lineage reconstruction can be requested here."
        )


def _require_affiliated_entity(
    corporate_entity_id: str | None,
    affiliated_entity_ids: frozenset[str],
) -> str:
    """Resolve the corporate scope the caller may already walk."""
    if corporate_entity_id:
        try:
            UUID(corporate_entity_id)
        except ValueError as exc:
            raise AnalysisRunInvalidRequest(
                "corporate_entity_id must be a UUID"
            ) from exc
        if corporate_entity_id not in affiliated_entity_ids:
            raise AnalysisRunForbiddenScope(
                "corporate entity is not visible to this account"
            )
        return corporate_entity_id
    if len(affiliated_entity_ids) == 1:
        return next(iter(affiliated_entity_ids))
    if not affiliated_entity_ids:
        raise AnalysisRunForbiddenScope(
            "this account has no corporate entity to reconstruct"
        )
    raise AnalysisRunInvalidRequest(
        "choose which corporate entity to reconstruct"
    )


def _as_utc(value: datetime) -> datetime:
    """Normalize a timestamptz or naive UTC value to aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _lock_entity_snapshot(
    conn: asyncpg.Connection,
    corporate_entity_id: str,
    not_after: datetime,
) -> asyncpg.Record:
    """Lock the latest snapshot already used for this corporate entity.

    A snapshot is an immutable capture (ADR 0013). This write reuses one
    that a prior run already bound to the entity so a first-time tenant
    cannot attach to another tenant's capture. ``not_after`` is the
    request clock: availability must already be knowable.
    """
    row = await conn.fetchrow(
        """
        select snap.analysis_source_snapshot_id,
               snap.snapshot_sha256,
               snap.maximum_available_time,
               snap.captured_at
          from analysis_source_snapshot snap
          join analysis_run run
            on run.analysis_source_snapshot_id = snap.analysis_source_snapshot_id
          join analysis_run_scope scope
            on scope.analysis_run_id = run.analysis_run_id
         where scope.scope_kind_code = $1
           and scope.corporate_entity_id = $2::uuid
           and snap.maximum_available_time <= $3
           and snap.captured_at <= $3
         order by snap.captured_at desc, run.requested_at desc
         limit 1
         for update of snap
        """,
        CORPORATE_SCOPE_KIND,
        corporate_entity_id,
        not_after,
    )
    if row is None:
        raise AnalysisRunSnapshotMissing(
            "Ask an administrator to capture a source snapshot for this "
            "entity, then request reconstruction again."
        )
    return row


def _same_request(
    existing: asyncpg.Record,
    *,
    snapshot_id: Any,
    configuration_sha256: str,
    knowledge_cutoff: datetime,
) -> bool:
    """True when the stored immutable request matches this retry."""
    return (
        str(existing["analysis_source_snapshot_id"]) == str(snapshot_id)
        and existing["run_kind_code"] == LINEAGE_RUN_KIND
        and existing["configuration_sha256"] == configuration_sha256
        and _as_utc(existing["knowledge_cutoff"]) == knowledge_cutoff
    )


async def create_pending_lineage_run(
    conn: asyncpg.Connection,
    *,
    account_id: str,
    affiliated_entity_ids: frozenset[str],
    run_kind_code: str,
    idempotency_key: str,
    corporate_entity_id: str | None = None,
    knowledge_cutoff: str | None = None,
) -> AnalysisRunWriteResult:
    """Insert run + corporate scope + pending event, or replay the same key.

    The snapshot row is locked first so a concurrent count freeze and
    this derivation cannot both commit (ADR 0013 lock order).
    """
    _require_lineage_kind(run_kind_code)
    key = canonical_idempotency_key(idempotency_key)
    entity_id = _require_affiliated_entity(corporate_entity_id, affiliated_entity_ids)
    requested_at = datetime.now(timezone.utc)
    snapshot = await _lock_entity_snapshot(conn, entity_id, requested_at)
    if knowledge_cutoff in (None, ""):
        cutoff = _as_utc(snapshot["maximum_available_time"])
    else:
        cutoff = parse_knowledge_cutoff(knowledge_cutoff, requested_at=requested_at)
        if cutoff < _as_utc(snapshot["maximum_available_time"]):
            raise AnalysisRunInvalidRequest(
                "knowledge_cutoff cannot precede the snapshot's latest admitted evidence"
            )
    digest = request_configuration_digest(
        run_kind_code=LINEAGE_RUN_KIND,
        scope_kind_code=CORPORATE_SCOPE_KIND,
        corporate_entity_id=entity_id,
        snapshot_sha256=snapshot["snapshot_sha256"],
        knowledge_cutoff=cutoff,
        configuration_schema_version=LINEAGE_SCHEMA_VERSION,
    )
    if not _HEX_DIGEST.match(digest):
        raise AnalysisRunInvalidRequest("configuration digest is not 64 hex characters")

    existing = await conn.fetchrow(
        """
        select analysis_run_id, analysis_source_snapshot_id, run_kind_code,
               configuration_sha256, knowledge_cutoff
          from analysis_run
         where requested_by_account_id = $1::uuid
           and idempotency_key = $2
        """,
        account_id,
        key,
    )
    if existing is not None:
        if _same_request(
            existing,
            snapshot_id=snapshot["analysis_source_snapshot_id"],
            configuration_sha256=digest,
            knowledge_cutoff=cutoff,
        ):
            return AnalysisRunWriteResult(str(existing["analysis_run_id"]), True)
        raise AnalysisRunConflict(str(existing["analysis_run_id"]))

    try:
        run_id = await conn.fetchval(
            """
            insert into analysis_run
                (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                 requested_by_account_id, knowledge_cutoff,
                 configuration_schema_version, configuration_sha256,
                 code_revision_sha, requested_at)
            values ($1, $2, $3, $4::uuid, $5, $6, $7, $8, $9)
            returning analysis_run_id
            """,
            snapshot["analysis_source_snapshot_id"],
            LINEAGE_RUN_KIND,
            key,
            account_id,
            cutoff,
            LINEAGE_SCHEMA_VERSION,
            digest,
            code_revision_digest(),
            requested_at,
        )
    except UniqueViolationError:
        raced = await conn.fetchrow(
            """
            select analysis_run_id, analysis_source_snapshot_id, run_kind_code,
                   configuration_sha256, knowledge_cutoff
              from analysis_run
             where requested_by_account_id = $1::uuid
               and idempotency_key = $2
            """,
            account_id,
            key,
        )
        if raced is None:
            raise
        if _same_request(
            raced,
            snapshot_id=snapshot["analysis_source_snapshot_id"],
            configuration_sha256=digest,
            knowledge_cutoff=cutoff,
        ):
            return AnalysisRunWriteResult(str(raced["analysis_run_id"]), True)
        raise AnalysisRunConflict(str(raced["analysis_run_id"])) from None

    await conn.execute(
        """
        insert into analysis_run_scope
            (analysis_run_id, scope_kind_code, corporate_entity_id)
        values ($1, $2, $3::uuid)
        """,
        run_id,
        CORPORATE_SCOPE_KIND,
        entity_id,
    )
    await conn.execute(
        """
        insert into analysis_run_status_event
            (analysis_run_id, status_ordinal, status_code, occurred_at)
        values ($1, 1, $2, $3)
        """,
        run_id,
        PENDING_STATUS,
        requested_at,
    )
    return AnalysisRunWriteResult(str(run_id), False)
