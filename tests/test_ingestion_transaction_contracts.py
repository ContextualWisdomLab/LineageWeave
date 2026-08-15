"""Regression contracts for ingestion transactions and review documentation."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from backend.app import corporate_entity_ingestion as corporate_ingestion
from backend.app import post_summary_ingestion as summary_ingestion
from lineageweave.corporate_hierarchy_inference import HierarchyProposal
from lineageweave.post_summary import (
    ACTOR_TYPE_ORGANIZATION,
    ACTOR_TYPE_TEAM,
    PostSummary,
    RoleResponsibility,
)
from lineageweave.relation_verification import STATUS_CORROBORATED


class _RecordedTransaction:
    """Record transaction entry and exit for one fake asyncpg connection."""

    def __init__(self, events: list[Any], owner: Any | None = None) -> None:
        self._events = events
        self._owner = owner

    async def __aenter__(self) -> "_RecordedTransaction":
        if self._owner is not None:
            assert not self._owner.in_transaction
            self._owner.in_transaction = True
        self._events.append("transaction:enter")
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> bool:
        self._events.append("transaction:exit")
        if self._owner is not None:
            self._owner.in_transaction = False
        return False


class _InferenceClient:
    """Return one verified root-company proposal without network access."""

    available = True

    def __init__(self, events: list[Any]) -> None:
        self._events = events

    def infer(self, organization_name: str, context_text: str) -> HierarchyProposal:
        self._events.append("inference")
        return HierarchyProposal(level_code="company", parent_name=None)


class _VerificationClient:
    """Corroborate the synthetic proposal while recording call order."""

    available = True

    def __init__(self, events: list[Any]) -> None:
        self._events = events

    def verify(self, subject: str, relation: str) -> SimpleNamespace:
        self._events.append("verification")
        return SimpleNamespace(status_code=STATUS_CORROBORATED)


class _CorporateConnection:
    """Minimal asyncpg-compatible connection for creation-lock behavior."""

    def __init__(
        self,
        events: list[Any],
        *,
        reloaded_rows: tuple[dict[str, Any], ...] = (),
        inserted_id: uuid.UUID | None = None,
        allow_insert: bool = True,
    ) -> None:
        self._events = events
        self._reloaded_rows = reloaded_rows
        self._inserted_id = inserted_id or uuid.uuid4()
        self._allow_insert = allow_insert

    def transaction(self) -> _RecordedTransaction:
        self._events.append("transaction:open")
        return _RecordedTransaction(self._events)

    async def execute(self, query: str, *args: Any) -> str:
        compact = " ".join(query.split())
        assert "pg_advisory_xact_lock" in compact
        self._events.append(("creation_lock", args, compact))
        return "SELECT 1"

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        compact = " ".join(query.split())
        assert compact == "select corporate_entity_id, entity_name from corporate_entity"
        self._events.append("candidate_reload")
        return list(self._reloaded_rows)

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any]:
        assert self._allow_insert, "locked candidate recheck should avoid insertion"
        compact = " ".join(query.split())
        assert compact.startswith("insert into corporate_entity")
        self._events.append("entity_insert")
        return {"corporate_entity_id": self._inserted_id}


def test_corporate_entity_creation_locks_rechecks_and_inserts_in_one_transaction() -> None:
    """Network verification precedes one transaction-scoped global creation lock."""
    events: list[Any] = []
    inserted_id = uuid.uuid4()
    connection = _CorporateConnection(events, inserted_id=inserted_id)
    candidates: list[Any] = []

    result = asyncio.run(
        corporate_ingestion.get_or_create_corporate_entity(
            connection,
            "Synthetic Energy",
            "Synthetic context",
            _InferenceClient(events),
            _VerificationClient(events),
            candidates,
        )
    )

    assert result == str(inserted_id)
    assert [candidate.entity_name for candidate in candidates] == ["Synthetic Energy"]
    assert events[:4] == [
        "inference",
        "verification",
        "transaction:open",
        "transaction:enter",
    ]
    lock_event = events[4]
    assert lock_event[0] == "creation_lock"
    assert lock_event[1] == ("lineageweave:corporate_entity_creation",)
    assert events[5:] == ["candidate_reload", "entity_insert", "transaction:exit"]


def test_locked_candidate_recheck_reuses_concurrently_created_entity() -> None:
    """A same-name row committed after inference wins over a duplicate insert."""
    events: list[Any] = []
    existing_id = uuid.uuid4()
    connection = _CorporateConnection(
        events,
        reloaded_rows=(
            {
                "corporate_entity_id": existing_id,
                "entity_name": "Synthetic Energy",
            },
        ),
        allow_insert=False,
    )
    candidates: list[Any] = []

    result = asyncio.run(
        corporate_ingestion.get_or_create_corporate_entity(
            connection,
            "Synthetic Energy",
            "Synthetic context",
            _InferenceClient(events),
            _VerificationClient(events),
            candidates,
        )
    )

    assert result == str(existing_id)
    assert [candidate.entity_name for candidate in candidates] == ["Synthetic Energy"]
    assert "entity_insert" not in events
    assert events[-1] == "transaction:exit"


class _SummaryConnection:
    """Minimal connection that records every post-summary database operation."""

    def __init__(self, events: list[Any]) -> None:
        self._events = events
        self.in_transaction = False

    def transaction(self) -> _RecordedTransaction:
        self._events.append("transaction:open")
        return _RecordedTransaction(self._events, self)

    async def execute(self, query: str, *args: Any) -> str:
        assert self.in_transaction
        compact = " ".join(query.split())
        self._events.append(("execute", compact))
        return "OK"

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        compact = " ".join(query.split())
        self._events.append(("fetchrow", compact))
        if compact.startswith("select korean_summary from post_summary_result"):
            assert not self.in_transaction
            return {"korean_summary": "합성 요약"}
        if compact.startswith("select person_id from cataloged_person"):
            assert self.in_transaction
            return None
        raise AssertionError(f"unexpected fetchrow query: {compact}")

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        compact = " ".join(query.split())
        self._events.append(("fetch", compact))
        assert not self.in_transaction
        if "from post_summary_event" in compact:
            return [{"event_text": "검토 완료"}]
        if "from post_summary_role" in compact:
            return [
                {
                    "actor_name": "Synthetic Design Team",
                    "responsibility": "도면 검토",
                    "actor_type_code": ACTOR_TYPE_TEAM,
                    "affiliated_organization_name": "Synthetic Energy",
                }
            ]
        raise AssertionError(f"unexpected fetch query: {compact}")


def test_post_summary_replacement_mentions_and_edges_share_one_transaction(monkeypatch) -> None:
    """Deletion, replacement, mention regeneration, and edges commit atomically."""
    events: list[Any] = []
    connection = _SummaryConnection(events)
    team_id = str(uuid.uuid4())

    async def load_candidates(conn) -> list[Any]:
        events.append("candidate_load")
        return []

    async def upsert_team(conn, team_name, organization_name, candidates) -> str:
        assert conn.in_transaction
        events.append("team_upsert")
        return team_id

    async def persist_edges(conn, post_id) -> list[Any]:
        assert conn.in_transaction
        events.append("edge_persist")
        return []

    monkeypatch.setattr(summary_ingestion, "_load_corporate_entity_candidates", load_candidates)
    monkeypatch.setattr(summary_ingestion, "upsert_team", upsert_team)
    monkeypatch.setattr(summary_ingestion, "persist_edges_for_post", persist_edges)

    summary = PostSummary(
        korean_summary="합성 요약",
        key_events=("검토 완료",),
        roles_and_responsibilities=(
            RoleResponsibility(
                actor_name="Synthetic Design Team",
                responsibility="도면 검토",
                actor_type_code=ACTOR_TYPE_TEAM,
                affiliated_organization_name="Synthetic Energy",
            ),
        ),
    )

    payload = asyncio.run(
        summary_ingestion.persist_post_summary(
            connection,
            str(uuid.uuid4()),
            summary,
        )
    )

    enter_index = events.index("transaction:enter")
    exit_index = events.index("transaction:exit")
    required_sql = (
        "delete from knowledge_graph_edge",
        "delete from post_team_mention",
        "delete from post_organization_mention",
        "delete from post_summary_result",
        "insert into post_summary_result",
        "insert into post_summary_event",
        "insert into post_summary_role",
        "insert into post_team_mention",
    )
    for fragment in required_sql:
        operation_index = next(
            index
            for index, event in enumerate(events)
            if isinstance(event, tuple)
            and event[0] == "execute"
            and fragment in event[1]
        )
        assert enter_index < operation_index < exit_index
    assert events.index("candidate_load") < enter_index
    assert enter_index < events.index("team_upsert") < exit_index
    assert enter_index < events.index("edge_persist") < exit_index
    assert payload["korean_summary"] == "합성 요약"


def test_organization_enrichment_finishes_before_summary_transaction(monkeypatch) -> None:
    """LLM verification and the advisory-lock transaction precede summary writes."""
    events: list[Any] = []
    connection = _SummaryConnection(events)
    corporate_entity_id = str(uuid.uuid4())

    async def load_candidates(conn) -> list[Any]:
        events.append(("candidate_load", conn.in_transaction))
        return []

    async def resolve_organization(
        conn,
        organization_name,
        context_text,
        inference_client,
        verification_client,
        candidates,
    ) -> str:
        events.append(("organization_resolve", conn.in_transaction))
        assert not conn.in_transaction
        return corporate_entity_id

    async def persist_edges(conn, post_id) -> list[Any]:
        assert conn.in_transaction
        events.append("edge_persist")
        return []

    monkeypatch.setattr(summary_ingestion, "_load_corporate_entity_candidates", load_candidates)
    monkeypatch.setattr(summary_ingestion, "get_or_create_corporate_entity", resolve_organization)
    monkeypatch.setattr(summary_ingestion, "persist_edges_for_post", persist_edges)

    summary = PostSummary(
        korean_summary="합성 요약",
        roles_and_responsibilities=(
            RoleResponsibility(
                actor_name="Synthetic Energy",
                responsibility="납품 일정 확정",
                actor_type_code=ACTOR_TYPE_ORGANIZATION,
            ),
        ),
    )

    asyncio.run(
        summary_ingestion.persist_post_summary(
            connection,
            str(uuid.uuid4()),
            summary,
        )
    )

    assert ("candidate_load", False) in events
    assert ("organization_resolve", False) in events
    resolve_index = events.index(("organization_resolve", False))
    enter_index = events.index("transaction:enter")
    exit_index = events.index("transaction:exit")
    mention_index = next(
        index
        for index, event in enumerate(events)
        if isinstance(event, tuple)
        and event[0] == "execute"
        and "insert into post_organization_mention" in event[1]
    )
    assert resolve_index < enter_index < mention_index < exit_index


def test_release_notes_describe_balanced_outer_emphasis_stripping() -> None:
    """Release notes must match the parser's reviewed normalization contract."""
    content = (Path(__file__).resolve().parents[1] / "CHANGELOG.md").read_text(
        encoding="utf-8"
    )
    assert "strips balanced outer Markdown emphasis from field values" in content
    assert "while still accepting emphasized field labels" in content
    assert "preserves Markdown emphasis in field values" not in content
