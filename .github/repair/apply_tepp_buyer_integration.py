#!/usr/bin/env python3
"""Apply the one-shot TEPP buyer integration repair to the #258 branch."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    """Read one repository-relative UTF-8 file."""
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    """Write one repository-relative UTF-8 file."""
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    """Replace exactly one literal occurrence or fail closed."""
    content = read(path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one exact match, found {count}")
    write(path, content.replace(old, new, 1))


def sub_once(path: str, pattern: str, replacement: str, *, flags: int = 0) -> None:
    """Replace exactly one regular-expression occurrence or fail closed."""
    content = read(path)
    updated, count = re.subn(pattern, replacement, content, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(
            f"{path}: expected one regex match, found {count}: {pattern!r}"
        )
    write(path, updated)


replace_once(
    "lineageweave/http_client.py",
    "def post_form(\n",
    '''def post_json_exact(
    url: str,
    payload: dict,
    *,
    headers: dict[str, str],
    timeout: float,
) -> dict:
    """POST an exact JSON object without LLM metadata enrichment.

    Closed external contracts such as TEPP reject unknown fields. This helper
    deliberately preserves the caller's wire object modulo JSON serialization
    while retaining the shared HTTP(S), TLS, timeout, and response-validation
    boundary.

    Raises:
        ValueError: ``url`` is not an ``http`` / ``https`` URL with a host.
        HttpClientError: the server responded with HTTP >= 400 or non-JSON.
    """
    status, raw = _request(
        "POST",
        url,
        body=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json", **headers},
        timeout=timeout,
    )
    hostname = urlparse(url).hostname or url
    if status >= 400:
        raise HttpClientError(f"HTTP {status} from {hostname}")
    return _decode_json_object(raw, hostname)


def post_form(
''',
)

write(
    "lineageweave/tepp_result.py",
    '''"""Strict TEPP accepted-envelope evidence for LineageWeave.

TEPP publishes an asynchronous ``AnalysisRunAccepted`` envelope containing
``contract_version``, opaque ``run_id``, ``run_state=accepted``, and the
caller's ``idempotency_key``. LineageWeave may store that acknowledgement as
aggregate transport evidence. It is not a completed psychometric result and
must never be presented as theta, uncertainty, a topic score, an item
parameter, or a calibrated estimate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

_ACCEPTED_FIELDS = frozenset(
    {"contract_version", "run_id", "run_state", "idempotency_key"}
)
_FORBIDDEN_KEY_PARTS = (
    "theta",
    "topic",
    "item_parameter",
    "membership",
    "uncertainty",
    "affiliation_count",
    "interval_count",
    "level_count",
)


@dataclass(frozen=True)
class TeppAcceptedEvidence:
    """Published transport acknowledgement that is safe to persist."""

    contract_version: int
    accepted_run_id: str
    run_state: str
    idempotency_key: str

    def evidence_sha256(self) -> str:
        """Return a stable digest of the four published acknowledgement fields."""
        material = json.dumps(
            {
                "accepted_run_id": self.accepted_run_id,
                "contract_version": self.contract_version,
                "idempotency_key": self.idempotency_key,
                "run_state": self.run_state,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _nonempty_text(value: Any) -> str | None:
    """Return stripped nonempty text, otherwise ``None``."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _contains_forbidden_measurement_key(value: Any) -> bool:
    """Return whether a nested object names an unpublished measurement field."""
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(part in normalized for part in _FORBIDDEN_KEY_PARTS):
                return True
            if _contains_forbidden_measurement_key(nested):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_forbidden_measurement_key(item) for item in value)
    return False


def parse_tepp_accepted_evidence(
    envelope: Any,
    *,
    expected_idempotency_key: str | None = None,
) -> TeppAcceptedEvidence | None:
    """Parse the exact published acknowledgement or fail closed.

    Unknown fields, a mismatched idempotency key, any non-``accepted`` state,
    and any measurement-looking key are rejected. This prevents a transport
    acknowledgement from being silently upgraded into a scientific result.
    """
    if not isinstance(envelope, dict) or set(envelope) != _ACCEPTED_FIELDS:
        return None
    if _contains_forbidden_measurement_key(envelope):
        return None
    if envelope.get("contract_version") != 1:
        return None
    accepted_run_id = _nonempty_text(envelope.get("run_id"))
    run_state = _nonempty_text(envelope.get("run_state"))
    idempotency_key = _nonempty_text(envelope.get("idempotency_key"))
    if accepted_run_id is None or run_state != "accepted" or idempotency_key is None:
        return None
    if (
        expected_idempotency_key is not None
        and idempotency_key != expected_idempotency_key
    ):
        return None
    return TeppAcceptedEvidence(
        contract_version=1,
        accepted_run_id=accepted_run_id,
        run_state=run_state,
        idempotency_key=idempotency_key,
    )
''',
)

replace_once(
    "backend/app/analysis_run_start.py",
    "from lineageweave.http_client import HttpClientError, post_json\n",
    "from lineageweave.http_client import HttpClientError, post_json_exact\n",
)
replace_once(
    "backend/app/analysis_run_start.py",
    "from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable\n",
    '''from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable
from lineageweave.tepp_result import TeppAcceptedEvidence, parse_tepp_accepted_evidence
''',
)
sub_once(
    "backend/app/analysis_run_start.py",
    r'''def configured_tepp_client\(transport_url: str = "", api_key: str = ""\) -> TeppClient:
.*?
    return TeppClient\(transport=transport\)
''',
    '''def configured_tepp_client(transport_url: str = "", api_key: str = "") -> TeppClient:
    """Build the credential-free LineageWeave -> TEPP HTTP client.

    ``TEPP_API_KEY`` remains an accepted legacy configuration argument so
    existing deployments do not crash during rollout, but its value is never
    forwarded. TEPP identifies LineageWeave using the published consumer
    header and rejects credential headers.
    """
    del api_key
    url = transport_url.strip()
    if not url:
        return TeppClient()

    def transport(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            headers = {
                "tepp-consumer": "lineageweave",
                "tepp-contract-version": str(payload["contract_version"]),
                "idempotency-key": str(payload["idempotency_key"]),
            }
            return post_json_exact(url, payload, headers=headers, timeout=30.0)
        except (HttpClientError, OSError, ValueError, TypeError, KeyError) as exc:
            raise TeppNotAvailable(str(exc)) from exc

    return TeppClient(transport=transport)
''',
    flags=re.S,
)
sub_once(
    "backend/app/analysis_run_start.py",
    r'''def _tepp_submission\(
    client: TeppClient,
    request: AnalysisRunRequest,
\) -> tuple\[str, str, dict\[str, Any\] \| None\]:
.*?
def tepp_submit_outcome\(
    client: TeppClient,
    request: AnalysisRunRequest,
\) -> tuple\[str, str\]:
    """Compatibility projection of the TEPP submission outcome\."""
    status_code, failure_code, _ = _tepp_submission\(client, request\)
    return status_code, failure_code
''',
    '''def _tepp_submission(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> tuple[str, str, TeppAcceptedEvidence | dict[str, Any] | None]:
    """Submit through ``tepp_client`` and classify the returned evidence.

    The published asynchronous acknowledgement leaves the run in ``Running``.
    It is persisted separately from a future provider-authoritative completed
    result. Malformed evidence and absent transports fail closed.
    """
    try:
        response = client.submit_analysis_run(request)
    except TeppNotAvailable:
        return _FAILED, "tepp_not_available", None
    accepted = parse_tepp_accepted_evidence(
        response,
        expected_idempotency_key=request.idempotency_key,
    )
    if accepted is not None:
        return _RUNNING, "", accepted
    if not isinstance(response, dict):
        return _FAILED, "tepp_result_not_persisted", None
    if response.get("status") not in {"completed", "succeeded"}:
        return _FAILED, "tepp_result_not_persisted", None
    if not isinstance(response.get("result"), dict):
        return _FAILED, "tepp_result_not_persisted", None
    remote_run_id = response.get("analysis_run_id") or response.get("run_id")
    if not isinstance(remote_run_id, str) or not remote_run_id.strip():
        return _FAILED, "tepp_result_not_persisted", None
    return _SUCCEEDED, "", response


def tepp_submit_outcome(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> tuple[str, str]:
    """Return the lifecycle projection without exposing provider payloads."""
    status_code, failure_code, _ = _tepp_submission(client, request)
    return status_code, failure_code
''',
    flags=re.S,
)
replace_once(
    "backend/app/analysis_run_start.py",
    '''    return True


def start_write_conflict_error() -> AnalysisRunStartError:
''',
    '''    return True


async def _persist_tepp_accepted(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    evidence: TeppAcceptedEvidence,
    received_at: datetime,
) -> bool:
    """Persist one idempotent TEPP acknowledgement without later mutation."""
    try:
        inserted = await conn.fetchval(
            """
            insert into analysis_run_tepp_accepted
                (analysis_run_id, contract_version, accepted_run_id,
                 run_state, idempotency_key, evidence_sha256,
                 received_at, recorded_at)
            values ($1, $2, $3, $4, $5, $6, $7, clock_timestamp())
            on conflict (analysis_run_id) do nothing
            returning true
            """,
            analysis_run_id,
            evidence.contract_version,
            evidence.accepted_run_id,
            evidence.run_state,
            evidence.idempotency_key,
            evidence.evidence_sha256(),
            received_at,
        )
        if inserted:
            return True
        stored = await conn.fetchrow(
            """
            select contract_version, accepted_run_id, run_state,
                   idempotency_key, evidence_sha256
            from analysis_run_tepp_accepted
            where analysis_run_id = $1
            """,
            analysis_run_id,
        )
    except (asyncpg.PostgresError, TypeError, ValueError):
        return False
    if stored is None:
        return False
    return (
        int(stored["contract_version"]) == evidence.contract_version
        and stored["accepted_run_id"] == evidence.accepted_run_id
        and stored["run_state"] == evidence.run_state
        and stored["idempotency_key"] == evidence.idempotency_key
        and stored["evidence_sha256"] == evidence.evidence_sha256()
    )


def start_write_conflict_error() -> AnalysisRunStartError:
''',
)
sub_once(
    "backend/app/analysis_run_start.py",
    r'''async def _deliver_tepp_measurement\(
    conn: asyncpg.Connection,
    \*,
    analysis_run_id: str,
    locked: asyncpg.Record,
    tepp_client: TeppClient,
\) -> None:
.*?\n    await _append_status\(
        conn,
        analysis_run_id,
        await _next_status_ordinal\(conn, analysis_run_id\),
        status_code,
        finished,
        failure_code,
    \)
''',
    '''async def _deliver_tepp_measurement(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    locked: asyncpg.Record,
    tepp_client: TeppClient,
) -> None:
    """Submit the frozen snapshot and persist only published TEPP evidence."""
    received_at = datetime.now(timezone.utc)
    request = tepp_run_request(
        idempotency_key=str(locked["idempotency_key"]),
        snapshot_sha256=str(locked["snapshot_sha256"]),
        knowledge_cutoff=locked["knowledge_cutoff"],
        corporate_entity_id=str(locked["corporate_entity_id"]),
    )
    status_code, failure_code, evidence = _tepp_submission(tepp_client, request)
    if status_code == _RUNNING and isinstance(evidence, TeppAcceptedEvidence):
        if await _persist_tepp_accepted(
            conn,
            analysis_run_id=analysis_run_id,
            evidence=evidence,
            received_at=received_at,
        ):
            return
        status_code = _FAILED
        failure_code = "tepp_accepted_not_persisted"
    elif status_code == _SUCCEEDED and isinstance(evidence, dict):
        if not await _persist_tepp_result(
            conn,
            analysis_run_id=analysis_run_id,
            envelope=evidence,
        ):
            status_code = _FAILED
            failure_code = "tepp_result_not_persisted"
    finished = datetime.now(timezone.utc)
    if finished < received_at:
        finished = received_at
    await _append_status(
        conn,
        analysis_run_id,
        await _next_status_ordinal(conn, analysis_run_id),
        status_code,
        finished,
        failure_code,
    )
''',
    flags=re.S,
)

replace_once(
    "backend/app/analysis_run_ingestion.py",
    "async def fetch_outbox_deliveries(\n",
    '''async def fetch_tepp_accepted_evidence(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> dict[str, Any] | None:
    """Return redacted TEPP acknowledgement evidence for a visible run."""
    try:
        row = await conn.fetchrow(
            """
            select contract_version, accepted_run_id, run_state,
                   evidence_sha256, received_at, recorded_at
            from analysis_run_tepp_accepted
            where analysis_run_id = $1::uuid
            """,
            analysis_run_id,
        )
    except asyncpg.UndefinedTableError:
        return None
    if row is None:
        return None
    return {
        "contract_version": int(row["contract_version"]),
        "accepted_run_id": row["accepted_run_id"],
        "run_state": row["run_state"],
        "evidence_sha256": row["evidence_sha256"],
        "received_at": _iso(row["received_at"]),
        "recorded_at": _iso(row["recorded_at"]),
        "evidence_kind": "aggregate_transport_evidence",
    }


async def fetch_outbox_deliveries(
''',
)
replace_once(
    "backend/app/analysis_run_ingestion.py",
    '''    detail["outbox_deliveries"] = await fetch_outbox_deliveries(conn, analysis_run_id)
    detail["visible_posts"] = await fetch_visible_scope_posts(
''',
    '''    detail["outbox_deliveries"] = await fetch_outbox_deliveries(conn, analysis_run_id)
    tepp_accepted = await fetch_tepp_accepted_evidence(conn, analysis_run_id)
    if tepp_accepted is not None:
        detail["tepp_accepted"] = tepp_accepted
    detail["visible_posts"] = await fetch_visible_scope_posts(
''',
)

write(
    "migrations/0047_analysis_run_tepp_accepted.sql",
    r'''-- Published TEPP AnalysisRunAccepted transport evidence (ADR 0090).
-- This is not a completed result, theta, topic score, item parameter, or
-- uncertainty estimate.

create table if not exists analysis_run_tepp_accepted (
    analysis_run_id uuid primary key references analysis_run (analysis_run_id),
    contract_version integer not null,
    accepted_run_id text not null,
    run_state text not null,
    idempotency_key text not null,
    evidence_sha256 text not null,
    received_at timestamptz not null,
    recorded_at timestamptz not null default clock_timestamp(),
    constraint analysis_run_tepp_accepted_contract_check check (contract_version = 1),
    constraint analysis_run_tepp_accepted_run_state_check check (run_state = 'accepted'),
    constraint analysis_run_tepp_accepted_run_id_check check (btrim(accepted_run_id) <> ''),
    constraint analysis_run_tepp_accepted_idempotency_check check (btrim(idempotency_key) <> ''),
    constraint analysis_run_tepp_accepted_digest_check check (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    constraint analysis_run_tepp_accepted_time_check check (received_at <= recorded_at)
);

create unique index if not exists analysis_run_tepp_accepted_remote_idx
    on analysis_run_tepp_accepted (accepted_run_id);

comment on table analysis_run_tepp_accepted is
    'One immutable TEPP accepted acknowledgement per analysis run; aggregate '
    'transport evidence, never a validated multilevel estimate.';

create or replace function reject_analysis_run_tepp_accepted_update()
returns trigger
language plpgsql
as $$
begin
    raise exception 'analysis_run_tepp_accepted_is_immutable';
end
$$;

drop trigger if exists analysis_run_tepp_accepted_update_reject
    on analysis_run_tepp_accepted;
create trigger analysis_run_tepp_accepted_update_reject
before update or delete on analysis_run_tepp_accepted
for each row execute function reject_analysis_run_tepp_accepted_update();

create or replace function purge_analysis_run_registry(approval_token text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
    run_count bigint;
    snapshot_count bigint;
begin
    if not exists (
        select 1 from analysis_run_retention_grant
        where database_role_name = session_user and revoked_at is null
    ) then
        raise exception 'analysis_run_retention_not_granted';
    end if;
    if not pg_has_role(session_user, 'analysis_run_retention_admin', 'member') then
        raise exception 'analysis_run_retention_not_admin';
    end if;
    if approval_token is distinct from 'approved-retention-purge' then
        raise exception 'analysis_run_retention_not_approved';
    end if;

    select count(*) into run_count from analysis_run;
    select count(*) into snapshot_count from analysis_source_snapshot;

    alter table analysis_run_status_event disable trigger analysis_run_status_event_delete_reject;
    alter table analysis_run_scope disable trigger analysis_run_scope_mutation_reject;
    alter table analysis_run disable trigger analysis_run_mutation_reject;
    if to_regclass('public.analysis_run_outbox') is not null then
        alter table analysis_run_outbox disable trigger analysis_run_outbox_mutation_reject;
        alter table analysis_run_outbox_delivery disable trigger analysis_run_outbox_delivery_mutation_reject;
    end if;
    if to_regclass('public.analysis_run_reconstruction') is not null then
        alter table analysis_run_reconstruction disable trigger analysis_run_reconstruction_update_reject;
        alter table analysis_run_lineage_edge disable trigger analysis_run_lineage_edge_update_reject;
    end if;
    alter table analysis_run_tepp_accepted disable trigger analysis_run_tepp_accepted_update_reject;
    if to_regclass('public.analysis_source_snapshot_member') is not null then
        alter table analysis_source_snapshot_member disable trigger analysis_source_snapshot_member_update_reject;
    end if;

    begin
        if to_regclass('public.analysis_run_outbox_delivery') is not null then
            delete from analysis_run_outbox_delivery;
            delete from analysis_run_outbox;
        end if;
        if to_regclass('public.analysis_run_lineage_edge') is not null then
            delete from analysis_run_lineage_edge;
        end if;
        if to_regclass('public.analysis_run_reconstruction') is not null then
            delete from analysis_run_reconstruction;
        end if;
        delete from analysis_run_tepp_accepted;
        if to_regclass('public.analysis_run_tepp_result') is not null then
            delete from analysis_run_tepp_result;
        end if;
        delete from analysis_run_status_event;
        delete from analysis_run_scope;
        delete from analysis_run;
        delete from analysis_source_count;
        if to_regclass('public.analysis_source_snapshot_member') is not null then
            delete from analysis_source_snapshot_member;
        end if;
        delete from analysis_source_snapshot;
    exception
        when others then
            alter table analysis_run enable trigger analysis_run_mutation_reject;
            alter table analysis_run_scope enable trigger analysis_run_scope_mutation_reject;
            alter table analysis_run_status_event enable trigger analysis_run_status_event_delete_reject;
            if to_regclass('public.analysis_run_outbox') is not null then
                alter table analysis_run_outbox enable trigger analysis_run_outbox_mutation_reject;
                alter table analysis_run_outbox_delivery enable trigger analysis_run_outbox_delivery_mutation_reject;
            end if;
            if to_regclass('public.analysis_run_reconstruction') is not null then
                alter table analysis_run_reconstruction enable trigger analysis_run_reconstruction_update_reject;
                alter table analysis_run_lineage_edge enable trigger analysis_run_lineage_edge_update_reject;
            end if;
            alter table analysis_run_tepp_accepted enable trigger analysis_run_tepp_accepted_update_reject;
            if to_regclass('public.analysis_source_snapshot_member') is not null then
                alter table analysis_source_snapshot_member enable trigger analysis_source_snapshot_member_update_reject;
            end if;
            raise;
    end;

    alter table analysis_run enable trigger analysis_run_mutation_reject;
    alter table analysis_run_scope enable trigger analysis_run_scope_mutation_reject;
    alter table analysis_run_status_event enable trigger analysis_run_status_event_delete_reject;
    if to_regclass('public.analysis_run_outbox') is not null then
        alter table analysis_run_outbox enable trigger analysis_run_outbox_mutation_reject;
        alter table analysis_run_outbox_delivery enable trigger analysis_run_outbox_delivery_mutation_reject;
    end if;
    if to_regclass('public.analysis_run_reconstruction') is not null then
        alter table analysis_run_reconstruction enable trigger analysis_run_reconstruction_update_reject;
        alter table analysis_run_lineage_edge enable trigger analysis_run_lineage_edge_update_reject;
    end if;
    alter table analysis_run_tepp_accepted enable trigger analysis_run_tepp_accepted_update_reject;
    if to_regclass('public.analysis_source_snapshot_member') is not null then
        alter table analysis_source_snapshot_member enable trigger analysis_source_snapshot_member_update_reject;
    end if;

    insert into analysis_run_retention_event (
        purged_run_count, purged_snapshot_count, approval_token_digest,
        invoking_session_role, invoking_current_role, client_network_address
    ) values (
        run_count, snapshot_count,
        encode(sha256(convert_to(approval_token, 'UTF8')), 'hex'),
        session_user, current_user, inet_client_addr()
    );
end
$$;
''',
)
write(
    "migrations/rollback/0047_analysis_run_tepp_accepted.sql",
    '''do $$
begin
    if exists (select 1 from analysis_run_tepp_accepted limit 1) then
        raise exception 'analysis_run_tepp_accepted_not_empty';
    end if;
end
$$;

drop trigger if exists analysis_run_tepp_accepted_update_reject
    on analysis_run_tepp_accepted;
drop function if exists reject_analysis_run_tepp_accepted_update();
drop table if exists analysis_run_tepp_accepted;
''',
)
replace_once(
    "docker/postgres-init/Dockerfile",
    "COPY migrations/0040_post_summary_contract.sql /docker-entrypoint-initdb.d/42-post-summary-contract.sql\n",
    '''COPY migrations/0040_post_summary_contract.sql /docker-entrypoint-initdb.d/42-post-summary-contract.sql
COPY migrations/0047_analysis_run_tepp_accepted.sql /docker-entrypoint-initdb.d/43-analysis-run-tepp-accepted.sql
''',
)
replace_once(
    "scripts/seed_demo_data.py",
    '''            cur.execute((migrations / "0025_role_person_catalog_identity.sql").read_text())
''',
    '''            cur.execute((migrations / "0025_role_person_catalog_identity.sql").read_text())
            cur.execute((migrations / "0027_analysis_run_tepp_result.sql").read_text())
            cur.execute((migrations / "0047_analysis_run_tepp_accepted.sql").read_text())
''',
)

replace_once(
    "frontend/src/api.ts",
    "export interface AnalysisRun {\n",
    '''export interface AnalysisRunTeppAccepted {
  contract_version: number;
  accepted_run_id: string;
  run_state: "accepted";
  evidence_sha256: string;
  received_at: string;
  recorded_at: string;
  evidence_kind: "aggregate_transport_evidence";
}

export interface AnalysisRun {
''',
)
replace_once(
    "frontend/src/api.ts",
    '''  reconstruction_result_sha256?: string;
  code_revision_sha?: string;
''',
    '''  reconstruction_result_sha256?: string;
  tepp_accepted?: AnalysisRunTeppAccepted;
  code_revision_sha?: string;
''',
)
write(
    "frontend/src/components/TeppMeasurementStatus.tsx",
    '''import type { AnalysisRunTeppAccepted } from "../api";

export function TeppMeasurementStatus({
  accepted,
}: {
  accepted?: AnalysisRunTeppAccepted;
}) {
  if (!accepted) return null;
  return (
    <section
      className="popup-section"
      aria-labelledby="tepp-measurement-status-heading"
      data-evidence-kind={accepted.evidence_kind}
    >
      <h4 id="tepp-measurement-status-heading">TEPP measurement</h4>
      <p role="status">
        TEPP accepted this measurement run. Calibrated estimates and uncertainty are still pending.
      </p>
      <dl>
        <dt>TEPP run</dt>
        <dd><code>{accepted.accepted_run_id}</code></dd>
        <dt>Accepted at</dt>
        <dd>{accepted.received_at}</dd>
        <dt>Evidence digest</dt>
        <dd><code>{accepted.evidence_sha256}</code></dd>
      </dl>
      <p className="post-meta">
        Next action: keep this run open until TEPP publishes a completed result contract.
      </p>
    </section>
  );
}
''',
)
write(
    "frontend/src/components/TeppMeasurementStatus.test.tsx",
    '''import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TeppMeasurementStatus } from "./TeppMeasurementStatus";

describe("TeppMeasurementStatus", () => {
  it("shows accepted transport evidence without claiming a score", () => {
    render(
      <TeppMeasurementStatus
        accepted={{
          contract_version: 1,
          accepted_run_id: "tepp-run-42",
          run_state: "accepted",
          evidence_sha256: "a".repeat(64),
          received_at: "2026-08-20T00:00:00+00:00",
          recorded_at: "2026-08-20T00:00:01+00:00",
          evidence_kind: "aggregate_transport_evidence",
        }}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Calibrated estimates");
    expect(screen.getByText("tepp-run-42")).toBeInTheDocument();
    expect(screen.queryByText(/theta/i)).not.toBeInTheDocument();
  });

  it("renders nothing before TEPP accepts the run", () => {
    const { container } = render(<TeppMeasurementStatus />);
    expect(container).toBeEmptyDOMElement();
  });
});
''',
)
replace_once(
    "frontend/src/App.tsx",
    'import { CutoffKnownBody } from "./components/CutoffKnownBody";\n',
    '''import { CutoffKnownBody } from "./components/CutoffKnownBody";
import { TeppMeasurementStatus } from "./components/TeppMeasurementStatus";
''',
)
replace_once(
    "frontend/src/App.tsx",
    '''    case "analysis_status_running":
      return "Refresh this run. Start already queued the work on the durable outbox.";
''',
    '''    case "analysis_status_running":
      if (run.run_kind_code === "analysis_run_tepp" && run.tepp_accepted) {
        return "TEPP accepted this run. Keep it open until calibrated results and uncertainty arrive.";
      }
      return "Refresh this run. Start already queued the work on the durable outbox.";
''',
)
replace_once(
    "frontend/src/App.tsx",
    '''          <h3>{analysisRunCaption(selected)}</h3>
          {selectedNextAction && <p className="post-meta">{selectedNextAction}</p>}
''',
    '''          <h3>{analysisRunCaption(selected)}</h3>
          <TeppMeasurementStatus accepted={selected.tepp_accepted} />
          {selectedNextAction && <p className="post-meta">{selectedNextAction}</p>}
''',
)

write(
    "tests/test_tepp_result.py",
    '''"""Published TEPP accepted evidence is not a completed measurement."""

from lineageweave.tepp_result import parse_tepp_accepted_evidence


def _accepted(**overrides):
    payload = {
        "contract_version": 1,
        "run_id": "tepp-run-42",
        "run_state": "accepted",
        "idempotency_key": "buyer-run-42",
    }
    payload.update(overrides)
    return payload


def test_published_accepted_envelope_is_transport_evidence() -> None:
    evidence = parse_tepp_accepted_evidence(
        _accepted(), expected_idempotency_key="buyer-run-42"
    )
    assert evidence is not None
    assert evidence.accepted_run_id == "tepp-run-42"
    assert evidence.run_state == "accepted"
    assert len(evidence.evidence_sha256()) == 64


def test_accepted_parser_fails_closed_on_unknown_or_measurement_fields() -> None:
    assert parse_tepp_accepted_evidence({"status": "accepted"}) is None
    assert parse_tepp_accepted_evidence(_accepted(theta=0.4)) is None
    assert parse_tepp_accepted_evidence(_accepted(extra=True)) is None
    assert parse_tepp_accepted_evidence(_accepted(run_state="completed")) is None
    assert parse_tepp_accepted_evidence(_accepted(contract_version=2)) is None
    assert parse_tepp_accepted_evidence(
        _accepted(), expected_idempotency_key="different"
    ) is None
''',
)
write(
    "tests/test_analysis_run_tepp_accepted_schema.py",
    '''"""Static contracts for normalized TEPP accepted evidence."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION = _ROOT / "migrations" / "0047_analysis_run_tepp_accepted.sql"
_ROLLBACK = _ROOT / "migrations" / "rollback" / "0047_analysis_run_tepp_accepted.sql"


def test_tepp_accepted_schema_is_normalized_immutable_and_purge_aware() -> None:
    migration = _MIGRATION.read_text(encoding="utf-8")
    assert "create table if not exists analysis_run_tepp_accepted" in migration
    assert "jsonb" not in migration.casefold()
    assert "before update or delete" in migration.casefold()
    assert "delete from analysis_run_tepp_accepted" in migration
    assert migration.index("delete from analysis_run_tepp_accepted") < migration.index(
        "delete from analysis_run_status_event"
    )
    assert "validated multilevel estimate" in migration


def test_tepp_accepted_rollback_refuses_nonempty_evidence() -> None:
    rollback = _ROLLBACK.read_text(encoding="utf-8")
    assert "analysis_run_tepp_accepted_not_empty" in rollback
    assert "drop table if exists analysis_run_tepp_accepted" in rollback
    assert "analysis_run_tepp_result" not in rollback
''',
)
replace_once(
    "tests/test_tepp_client.py",
    '''def test_configured_transport_sends_optional_bearer_key(monkeypatch: pytest.MonkeyPatch) -> None:
    received = {}

    def fake_post_json(url: str, payload: dict, *, headers: dict, timeout: float) -> dict:
        received.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return {"status": "accepted"}

    monkeypatch.setattr("backend.app.analysis_run_start.post_json", fake_post_json)
    client = configured_tepp_client("https://tepp.example/v1/analysis-runs", "test-key")

    client.submit_analysis_run(_sample_request())

    assert received["headers"] == {"authorization": "Bearer test-key"}
    assert received["payload"] == _sample_request().to_json()
''',
    '''def test_configured_transport_sends_exact_consumer_headers_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received = {}

    def fake_post_json_exact(
        url: str,
        payload: dict,
        *,
        headers: dict,
        timeout: float,
    ) -> dict:
        received.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return {
            "contract_version": 1,
            "run_id": "tepp-run-42",
            "run_state": "accepted",
            "idempotency_key": payload["idempotency_key"],
        }

    monkeypatch.setattr(
        "backend.app.analysis_run_start.post_json_exact", fake_post_json_exact
    )
    client = configured_tepp_client(
        "https://tepp.example/v1/analysis-runs",
        "legacy-key-that-must-not-be-forwarded",
    )

    result = client.submit_analysis_run(_sample_request())

    assert result["run_state"] == "accepted"
    assert received["headers"] == {
        "tepp-consumer": "lineageweave",
        "tepp-contract-version": "1",
        "idempotency-key": "demo-run-1",
    }
    assert received["payload"] == _sample_request().to_json()
    assert set(received["payload"]) == {
        "contract_version",
        "idempotency_key",
        "tenant_workspace_id",
        "snapshot_id",
        "knowledge_cutoff",
        "model_contract_version",
        "output_profile",
    }
''',
)
replace_once(
    "tests/test_analysis_run_start.py",
    '''def test_tepp_submit_outcome_does_not_persist_an_empty_envelope() -> None:
    """An accepted envelope is not a persistable measurement."""

    class _Accepting(TeppClient):
        def __init__(self) -> None:
            super().__init__(transport=lambda _payload: {"status": "accepted"})

    status, failure = tepp_submit_outcome(_Accepting(), _tepp_request())
    assert status == "analysis_status_failed"
    assert failure == "tepp_result_not_persisted"
''',
    '''def test_tepp_submit_outcome_keeps_a_published_acknowledgement_running() -> None:
    """A strict acknowledgement is evidence, not a score or failure."""

    class _Accepting(TeppClient):
        def __init__(self) -> None:
            super().__init__(
                transport=lambda payload: {
                    "contract_version": 1,
                    "run_id": "tepp-run-42",
                    "run_state": "accepted",
                    "idempotency_key": payload["idempotency_key"],
                }
            )

    status, failure = tepp_submit_outcome(_Accepting(), _tepp_request())
    assert status == "analysis_status_running"
    assert failure == ""


def test_tepp_submit_outcome_rejects_a_bare_accepted_word() -> None:
    """An unversioned status string is not TEPP's published evidence."""
    client = TeppClient(transport=lambda _payload: {"status": "accepted"})
    status, failure = tepp_submit_outcome(client, _tepp_request())
    assert status == "analysis_status_failed"
    assert failure == "tepp_result_not_persisted"
''',
)

write(
    "docs/adr/0090-tepp-accepted-buyer-evidence.md",
    '''# ADR 0090: TEPP accepted evidence stays Running

## Status

Accepted

## Context

The Buyer stack could create a TEPP run, but its HTTP transport added generic
LLM metadata and optional bearer credentials to a closed seven-field contract.
TEPP's live listener admitted only Naruon. When TEPP returned its published
asynchronous acknowledgement, LineageWeave treated it as a missing completed
result and moved the run to Failed.

## Decision

- TEPP admits the published `lineageweave` consumer without credentials.
- LineageWeave sends the exact `AnalysisRunRequest` body and consumer,
  contract-version, and idempotency headers.
- `AnalysisRunAccepted` is immutable aggregate transport evidence.
- A stored acknowledgement leaves the analysis run in Running.
- The buyer sees the opaque TEPP run ID, receipt time, digest, and the next
  action, while calibrated results and uncertainty remain explicitly pending.
- Only a future versioned completed-result contract may move a TEPP run to
  Succeeded.

## Consequences

The integration is modular and fail-closed without shared database access.
No theta, topic score, item parameter, membership weight, or uncertainty is
invented. Consumer identity is part of TEPP's idempotency namespace so Naruon
and LineageWeave cannot replay each other's accepted runs.
''',
)
write(
    "CHANGELOG.d/2.12.6-tepp-buyer-integration.md",
    '''### Fixed

- Connected LineageWeave to TEPP's published asynchronous analysis-run boundary
  with an exact credential-free request, consumer-scoped idempotency, immutable
  accepted evidence, and buyer-visible pending-result guidance.
- A valid TEPP acknowledgement now keeps the run Running instead of falsely
  marking it Failed or fabricating a completed psychometric result.
''',
)
