"""Regression contracts for ingestion transactions and review documentation."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app import corporate_entity_ingestion as corporate_ingestion
from backend.app import keyman_ingestion
from backend.app import post_summary_ingestion as summary_ingestion
from lineageweave.corporate_hierarchy_inference import HierarchyProposal
from lineageweave.corporate_hierarchy_resolution import score_corporate_entity
from lineageweave.keyman_extraction import OUR_SIDE, PersonMention
from lineageweave.knowledge_graph import NODE_PERSON
from lineageweave.post_summary import (
    ACTOR_TYPE_ORGANIZATION,
    ACTOR_TYPE_PERSON,
    ACTOR_TYPE_TEAM,
    POST_SUMMARY_CONTRACT_VERSION,
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
        if "organization_name_resolution" in compact:
            return []
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

    assert result == (str(inserted_id), None)
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

    assert result == (str(existing_id), None)
    assert [candidate.entity_name for candidate in candidates] == ["Synthetic Energy"]
    assert "entity_insert" not in events
    assert events[-1] == "transaction:exit"


def test_prepared_sibling_alias_reuses_first_applied_catalog_entity() -> None:
    """Sibling plans re-score the evolving snapshot before creating a row."""
    events: list[Any] = []
    inserted_id = uuid.uuid4()
    connection = _CorporateConnection(events, inserted_id=inserted_id)
    candidates: list[Any] = []

    async def prepare_then_apply() -> tuple[
        tuple[str | None, str | None],
        tuple[str | None, str | None],
    ]:
        first = await corporate_ingestion.prepare_corporate_entity_resolution(
            "Alpha",
            "Synthetic sibling-alias context",
            _InferenceClient(events),
            _VerificationClient(events),
            candidates,
        )
        second = await corporate_ingestion.prepare_corporate_entity_resolution(
            "Alphx",
            "Synthetic sibling-alias context",
            _InferenceClient(events),
            _VerificationClient(events),
            candidates,
        )
        first_result = await corporate_ingestion.apply_prepared_corporate_entity_resolution(
            connection,
            first,
            candidates,
        )
        second_result = await corporate_ingestion.apply_prepared_corporate_entity_resolution(
            connection,
            second,
            candidates,
        )
        return first_result, second_result

    first_result, second_result = asyncio.run(prepare_then_apply())

    assert first_result == second_result == (str(inserted_id), None)
    assert [event for event in events if event == "entity_insert"] == ["entity_insert"]
    assert [candidate.entity_name for candidate in candidates] == ["Alpha"]
    assert score_corporate_entity("Alphx", candidates).top_score == pytest.approx(0.8)


def test_prepared_child_excludes_resolved_parent_from_alias_reuse() -> None:
    """A fuzzy parent name cannot collapse a corroborated child hierarchy."""
    events: list[Any] = []
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()
    inserted_rows: list[dict[str, Any]] = []

    class HierarchyInference:
        available = True

        def infer(self, organization_name: str, _context_text: str) -> HierarchyProposal:
            if organization_name == "Synthetiqx":
                return HierarchyProposal(level_code="plant", parent_name="Synthetic")
            return HierarchyProposal(level_code="company", parent_name=None)

    class HierarchyVerification:
        available = True

        def verify(self, _subject: str, _relation: str) -> SimpleNamespace:
            return SimpleNamespace(status_code=STATUS_CORROBORATED)

    class HierarchyConnection:
        def transaction(self) -> _RecordedTransaction:
            return _RecordedTransaction(events)

        async def execute(self, query: str, *_args: Any) -> str:
            assert "pg_advisory_xact_lock" in query
            return "SELECT 1"

        async def fetch(self, _query: str, *_args: Any) -> list[dict[str, Any]]:
            if "organization_name_resolution" in _query:
                return []
            return list(inserted_rows)

        async def fetchrow(self, query: str, *args: Any) -> dict[str, uuid.UUID]:
            assert "insert into corporate_entity" in query
            organization_name = args[2]
            entity_id = parent_id if organization_name == "Synthetic" else child_id
            inserted_rows.append(
                {
                    "corporate_entity_id": entity_id,
                    "entity_name": organization_name,
                    "parent_entity_id": args[0],
                }
            )
            return {"corporate_entity_id": entity_id}

    async def prepare_parent_and_child() -> tuple[
        tuple[str | None, str | None],
        tuple[str | None, str | None],
        list[Any],
    ]:
        candidates: list[Any] = []
        inference = HierarchyInference()
        verification = HierarchyVerification()
        parent = await corporate_ingestion.prepare_corporate_entity_resolution(
            "Synthetic",
            "Synthetic parent-child context",
            inference,
            verification,
            candidates,
        )
        child = await corporate_ingestion.prepare_corporate_entity_resolution(
            "Synthetiqx",
            "Synthetic parent-child context",
            inference,
            verification,
            candidates,
        )
        connection = HierarchyConnection()
        parent_result = (
            await corporate_ingestion.apply_prepared_corporate_entity_resolution(
                connection,
                parent,
                candidates,
            )
        )
        child_result = (
            await corporate_ingestion.apply_prepared_corporate_entity_resolution(
                connection,
                child,
                candidates,
            )
        )
        return parent_result, child_result, candidates

    parent_result, child_result, candidates = asyncio.run(prepare_parent_and_child())

    assert score_corporate_entity("Synthetiqx", candidates[:1]).top_score == pytest.approx(
        0.8421052631578947
    )
    assert parent_result == (str(parent_id), None)
    assert child_result == (str(child_id), None)
    assert [row["entity_name"] for row in inserted_rows] == ["Synthetic", "Synthetiqx"]
    assert inserted_rows[1]["parent_entity_id"] == str(parent_id)


def test_prepared_parent_chain_applies_parent_before_child_without_provider_locks() -> None:
    """The composite caller preserves provider-first, parent-first semantics."""
    events: list[Any] = []
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()

    class ParentInference:
        available = True

        def infer(self, organization_name: str, _context_text: str) -> HierarchyProposal:
            events.append(("inference", organization_name))
            if organization_name == "Synthetic Child":
                return HierarchyProposal(
                    level_code="plant",
                    parent_name="Synthetic Parent",
                )
            return HierarchyProposal(level_code="company", parent_name=None)

    class ParentVerification:
        available = True

        def verify(self, subject: str, relation: str) -> SimpleNamespace:
            events.append(("verification", subject, relation))
            return SimpleNamespace(status_code=STATUS_CORROBORATED)

    class ParentConnection:
        def transaction(self) -> _RecordedTransaction:
            events.append("transaction:open")
            return _RecordedTransaction(events)

        async def execute(self, query: str, *_args: Any) -> str:
            assert "pg_advisory_xact_lock" in query
            events.append("creation_lock")
            return "SELECT 1"

        async def fetch(self, _query: str, *_args: Any) -> list[Any]:
            return []

        async def fetchrow(self, query: str, *args: Any) -> dict[str, uuid.UUID]:
            assert "insert into corporate_entity" in query
            organization_name = args[2]
            events.append(("entity_insert", organization_name, args[0]))
            return {
                "corporate_entity_id": (
                    parent_id if organization_name == "Synthetic Parent" else child_id
                )
            }

    result = asyncio.run(
        corporate_ingestion.get_or_create_corporate_entity(
            ParentConnection(),
            "Synthetic Child",
            "Synthetic parent-chain context",
            ParentInference(),
            ParentVerification(),
            [],
        )
    )

    assert result == (str(child_id), None)
    inserts = [event for event in events if isinstance(event, tuple) and event[0] == "entity_insert"]
    assert inserts == [
        ("entity_insert", "Synthetic Parent", None),
        ("entity_insert", "Synthetic Child", str(parent_id)),
    ]
    first_transaction = events.index("transaction:open")
    last_provider = max(
        index
        for index, event in enumerate(events)
        if isinstance(event, tuple) and event[0] in {"inference", "verification"}
    )
    assert last_provider < first_transaction


class _SummaryConnection:
    """Minimal connection that records every post-summary database operation."""

    def __init__(self, events: list[Any]) -> None:
        self._events = events
        self.in_transaction = False
        self.summary_input_sha256: str | None = None

    def transaction(self) -> _RecordedTransaction:
        self._events.append("transaction:open")
        return _RecordedTransaction(self._events, self)

    async def execute(self, query: str, *args: Any) -> str:
        assert self.in_transaction
        compact = " ".join(query.split())
        self._events.append(("execute", compact, args))
        if compact.startswith("insert into post_summary_result"):
            assert "summary_input_sha256" in compact
            self.summary_input_sha256 = args[-1]
        return "OK"

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        compact = " ".join(query.split())
        self._events.append(("fetchrow", compact))
        if compact.startswith(
            "select korean_summary, summary_contract_version, summary_input_sha256 "
            "from post_summary_result"
        ):
            assert self.in_transaction
            return {
                "korean_summary": "합성 요약",
                "summary_contract_version": POST_SUMMARY_CONTRACT_VERSION,
                "summary_input_sha256": self.summary_input_sha256,
            }
        if compact.startswith("select resolved_organization_name, verification_status_code"):
            assert not self.in_transaction
            return None
        if compact.startswith("select person_id from cataloged_person"):
            assert self.in_transaction
            return None
        raise AssertionError(f"unexpected fetchrow query: {compact}")

    async def fetchval(self, query: str, *args: Any) -> Any:
        compact = " ".join(query.split())
        self._events.append(("fetchval", compact))
        if compact.startswith("select source_detail_state_code from source_post"):
            assert not self.in_transaction
            return None
        raise AssertionError(f"unexpected fetchval query: {compact}")

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        compact = " ".join(query.split())
        self._events.append(("fetch", compact))
        if "from organization_name_resolution" in compact:
            assert not self.in_transaction
            return []
        assert self.in_transaction
        if "from post_summary_action" in compact:
            return []
        if "from post_summary_quantitative_observation" in compact:
            return []
        if "from post_summary_source_fact" in compact:
            return []
        if "from post_summary_semantic_relationship" in compact:
            return []
        if "from post_summary_event_clue" in compact:
            return []
        if "from post_summary_event" in compact:
            return [{"event_text": "검토 완료"}]
        if "from post_project_mention" in compact:
            return []
        if "from post_summary_role" in compact:
            assert "entity_name" not in compact
            assert "cataloged_corporate_entity_id" in compact
            return [
                {
                    "actor_name": "Synthetic Design Team",
                    "responsibility_text": "도면 검토",
                    "actor_type_code": ACTOR_TYPE_TEAM,
                    "affiliated_organization_name": "Synthetic Energy",
                    "cataloged_team_id": None,
                    "cataloged_corporate_entity_id": None,
                    "cataloged_person_id": None,
                    "cataloged_affiliated_corporate_entity_id": None,
                    "catalog_unresolved_reason_code": None,
                    "affiliation_catalog_unresolved_reason_code": None,
                }
            ]
        if "organization_name_resolution" in compact:
            return []
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

    async def current_input(*_args, **_kwargs) -> bool:
        events.append("input_lock")
        return True

    monkeypatch.setattr(summary_ingestion, "_lock_current_summary_input", current_input)

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
            post_body="Synthetic normalized summary input.",
            expected_source_body_sha256=hashlib.sha256(
                b"Synthetic normalized summary input."
            ).hexdigest(),
        )
    )

    enter_index = events.index("transaction:enter")
    lock_index = events.index("input_lock")
    exit_index = events.index("transaction:exit")
    required_sql = (
        "delete from post_summary_person_mention",
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
    assert enter_index < lock_index < events.index("team_upsert") < exit_index
    assert enter_index < events.index("edge_persist") < exit_index
    assert payload["korean_summary"] == "합성 요약"
    assert connection.summary_input_sha256 == hashlib.sha256(
        b"Synthetic normalized summary input."
    ).hexdigest()


def test_summary_source_revision_after_provider_work_preserves_prior_projection(
    monkeypatch,
) -> None:
    events: list[Any] = []
    connection = _SummaryConnection(events)
    proposals: list[str] = []
    catalog_writes: list[str] = []

    async def stale_input(*_args, **_kwargs) -> bool:
        return False

    async def must_not_replace(*_args, **_kwargs) -> None:
        raise AssertionError("stale provider output must not replace summary projections")

    async def load_candidates(*_args, **_kwargs) -> list[Any]:
        return []

    async def prepare_organization(*_args, **_kwargs):
        proposals.append("organization")
        return object()

    async def prepare_affiliation(*_args, **_kwargs):
        proposals.append("affiliation")
        return object()

    async def apply_organization(*_args, **_kwargs):
        catalog_writes.append("organization")
        return None, "reason_no_catalog_entry"

    async def apply_affiliation(*_args, **_kwargs):
        catalog_writes.append("affiliation")
        return "Synthetic Affiliate", "Synthetic Affiliate", None, None

    monkeypatch.setattr(summary_ingestion, "_lock_current_summary_input", stale_input)
    monkeypatch.setattr(summary_ingestion, "_replace_summary_projection", must_not_replace)
    monkeypatch.setattr(summary_ingestion, "_load_corporate_entity_candidates", load_candidates)
    monkeypatch.setattr(
        summary_ingestion,
        "prepare_corporate_entity_resolution",
        prepare_organization,
        raising=False,
    )
    monkeypatch.setattr(
        summary_ingestion,
        "prepare_affiliated_organization",
        prepare_affiliation,
        raising=False,
    )
    monkeypatch.setattr(
        summary_ingestion,
        "apply_prepared_corporate_entity_resolution",
        apply_organization,
        raising=False,
    )
    monkeypatch.setattr(
        summary_ingestion,
        "apply_prepared_affiliated_organization",
        apply_affiliation,
        raising=False,
    )

    with pytest.raises(RuntimeError, match="no longer current"):
        asyncio.run(
            summary_ingestion.persist_post_summary(
                connection,
                str(uuid.uuid4()),
                PostSummary(
                    korean_summary="합성 요약이다.",
                    roles_and_responsibilities=(
                        RoleResponsibility(
                            actor_name="Synthetic Organization",
                            responsibility="합성 책임",
                            actor_type_code=ACTOR_TYPE_ORGANIZATION,
                        ),
                        RoleResponsibility(
                            actor_name="Synthetic Person",
                            responsibility="합성 후속",
                            actor_type_code=ACTOR_TYPE_PERSON,
                            affiliated_organization_name="Synthetic Affiliate",
                        ),
                    ),
                ),
                post_body="Synthetic provider input.",
                expected_source_body_sha256=hashlib.sha256(
                    b"Synthetic original source."
                ).hexdigest(),
                require_image_evidence=False,
            )
        )

    assert not any(
        isinstance(event, tuple)
        and event[0] == "execute"
        and "delete from post_summary_result" in event[1]
        for event in events
    )
    assert proposals == ["organization", "affiliation"]
    assert catalog_writes == []


def test_blocking_organization_provider_finishes_before_current_source_lock(
    monkeypatch,
) -> None:
    """Network proposal work never holds the current source transaction."""
    events: list[Any] = []
    connection = _SummaryConnection(events)
    corporate_entity_id = str(uuid.uuid4())
    provider_started = asyncio.Event()
    provider_release = asyncio.Event()
    prepared = object()

    async def load_candidates(conn) -> list[Any]:
        events.append(("candidate_load", conn.in_transaction))
        return []

    async def prepare_organization(*_args, **_kwargs):
        events.append(("organization_prepare", connection.in_transaction))
        provider_started.set()
        await provider_release.wait()
        return prepared

    async def apply_organization(conn, proposal, candidates) -> tuple[str, str | None]:
        assert proposal is prepared
        events.append(("organization_apply", conn.in_transaction))
        assert conn.in_transaction
        return corporate_entity_id, None

    async def persist_edges(conn, post_id) -> list[Any]:
        assert conn.in_transaction
        events.append("edge_persist")
        return []

    monkeypatch.setattr(summary_ingestion, "_load_corporate_entity_candidates", load_candidates)
    monkeypatch.setattr(
        summary_ingestion,
        "prepare_corporate_entity_resolution",
        prepare_organization,
        raising=False,
    )
    monkeypatch.setattr(
        summary_ingestion,
        "apply_prepared_corporate_entity_resolution",
        apply_organization,
        raising=False,
    )
    monkeypatch.setattr(summary_ingestion, "persist_edges_for_post", persist_edges)

    async def current_input(*_args, **_kwargs) -> bool:
        events.append("input_lock")
        return True

    monkeypatch.setattr(summary_ingestion, "_lock_current_summary_input", current_input)

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

    async def persist_while_provider_is_blocked() -> bool:
        task = asyncio.create_task(
            summary_ingestion.persist_post_summary(
                connection,
                str(uuid.uuid4()),
                summary,
                post_body="Synthetic organization evidence.",
                expected_source_body_sha256=hashlib.sha256(
                    b"Synthetic organization evidence."
                ).hexdigest(),
            )
        )
        await asyncio.wait_for(provider_started.wait(), timeout=1)
        lock_was_held = connection.in_transaction
        provider_release.set()
        await task
        return lock_was_held

    assert asyncio.run(persist_while_provider_is_blocked()) is False

    assert ("candidate_load", False) in events
    assert ("organization_prepare", False) in events
    assert ("organization_apply", True) in events
    prepare_index = events.index(("organization_prepare", False))
    apply_index = events.index(("organization_apply", True))
    enter_index = events.index("transaction:enter")
    lock_index = events.index("input_lock")
    exit_index = events.index("transaction:exit")
    mention_index = next(
        index
        for index, event in enumerate(events)
        if isinstance(event, tuple)
        and event[0] == "execute"
        and "insert into post_organization_mention" in event[1]
    )
    role_insert = next(
        event[1]
        for event in events
        if isinstance(event, tuple)
        and event[0] == "execute"
        and "insert into post_summary_role" in event[1]
    )
    assert "cataloged_corporate_entity_id" in role_insert
    assert "cataloged_person_id" in role_insert
    assert prepare_index < enter_index < lock_index < apply_index < mention_index < exit_index


class _KeymanConnection:
    """Record whether organization enrichment runs outside the write transaction."""

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

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        compact = " ".join(query.split())
        self._events.append(("fetch", compact))
        if compact == "select corporate_entity_id, entity_name from corporate_entity":
            assert not self.in_transaction
            return []
        if "organization_name_resolution" in compact:
            assert not self.in_transaction
            return []
        if compact.startswith("select person_id, last_known_job_title"):
            assert self.in_transaction
            return []
        raise AssertionError(f"unexpected fetch query: {compact}")

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        assert self.in_transaction
        compact = " ".join(query.split())
        self._events.append(("fetchrow", compact))
        if compact.startswith("select person_id, last_known_job_title"):
            return None
        if compact.startswith("insert into cataloged_person"):
            return {"person_id": uuid.uuid4()}
        raise AssertionError(f"unexpected fetchrow query: {compact}")


def test_keyman_organization_enrichment_finishes_before_write_transaction(monkeypatch) -> None:
    """LLM resolution and hierarchy creation must not hold the Keyman write lock."""
    events: list[Any] = []
    connection = _KeymanConnection(events)
    corporate_entity_id = str(uuid.uuid4())

    prepared = object()

    async def prepare_affiliation(conn, *_args, **_kwargs):
        events.append(("organization_resolve", conn.in_transaction))
        assert not conn.in_transaction
        return prepared

    async def apply_affiliation(
        conn,
        proposal,
        candidates,
    ) -> tuple[str, str, str | None, str | None]:
        assert proposal is prepared
        events.append(("organization_create", conn.in_transaction))
        assert not conn.in_transaction
        return "AGP", "Aurora Grid Power", corporate_entity_id, None

    class _Client:
        available = True

        def extract(self, post_title: str, post_body: str) -> list[PersonMention]:
            return [
                PersonMention(
                    "Ada West",
                    OUR_SIDE,
                    affiliated_organization_names=("AGP",),
                )
            ]

    monkeypatch.setattr(
        keyman_ingestion,
        "prepare_affiliated_organization",
        prepare_affiliation,
    )
    monkeypatch.setattr(
        keyman_ingestion,
        "apply_prepared_affiliated_organization",
        apply_affiliation,
    )

    asyncio.run(
        keyman_ingestion.ingest_post_keymen(
            connection,
            _Client(),
            str(uuid.uuid4()),
            "Synthetic post",
            "Ada West at AGP followed up.",
            persist_graph=False,
        )
    )

    assert ("organization_resolve", False) in events
    assert ("organization_create", False) in events
    resolve_index = events.index(("organization_resolve", False))
    create_index = events.index(("organization_create", False))
    enter_index = events.index("transaction:enter")
    mention_index = next(
        index
        for index, event in enumerate(events)
        if isinstance(event, tuple)
        and event[0] == "execute"
        and "insert into post_person_mention" in event[1]
    )
    assert resolve_index < enter_index
    assert create_index < enter_index < mention_index


def test_release_notes_describe_balanced_outer_emphasis_stripping() -> None:
    """Release notes must match the parser's reviewed normalization contract."""
    content = (Path(__file__).resolve().parents[1] / "CHANGELOG.md").read_text(
        encoding="utf-8"
    )
    assert "strips balanced outer Markdown emphasis from field values" in content
    assert "while still accepting emphasized field labels" in content
    assert "preserves Markdown emphasis in field values" not in content


def test_fetch_persisted_summary_returns_stored_person_catalog_id() -> None:
    """A persisted person role keeps catalog_node_id for the chip button."""

    person_id = str(uuid.uuid4())
    summary_input = "Synthetic person projection evidence."
    summary_digest = hashlib.sha256(summary_input.encode("utf-8")).hexdigest()
    events: list[Any] = []

    class _PersonFetchConnection:
        """Return one stored person catalog id without a live database."""

        async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
            compact = " ".join(query.split())
            events.append(("fetchrow", compact))
            if compact.startswith(
                "select korean_summary, summary_contract_version, summary_input_sha256 "
                "from post_summary_result"
            ):
                return {
                    "korean_summary": "합성 요약",
                    "summary_contract_version": POST_SUMMARY_CONTRACT_VERSION,
                    "summary_input_sha256": summary_digest,
                }
            raise AssertionError(f"unexpected fetchrow query: {compact}")

        async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
            compact = " ".join(query.split())
            events.append(("fetch", compact))
            if "from post_summary_action" in compact:
                return []
            if "from post_summary_quantitative_observation" in compact:
                return []
            if "from post_summary_source_fact" in compact:
                return []
            if "from post_summary_semantic_relationship" in compact:
                return []
            if "from post_summary_event_clue" in compact:
                return []
            if "from post_summary_event" in compact:
                return []
            if "from post_project_mention" in compact:
                return []
            if "from post_summary_role" in compact:
                assert "cataloged_person_id" in compact
                return [
                    {
                        "actor_name": "Priya Nair",
                        "responsibility_text": "고객 측 수신",
                        "actor_type_code": ACTOR_TYPE_PERSON,
                        "affiliated_organization_name": "Northridge Grid",
                        "cataloged_team_id": None,
                        "cataloged_corporate_entity_id": None,
                        "cataloged_person_id": person_id,
                        "cataloged_affiliated_corporate_entity_id": None,
                        "catalog_unresolved_reason_code": None,
                        "affiliation_catalog_unresolved_reason_code": None,
                    }
                ]
            raise AssertionError(f"unexpected fetch query: {compact}")

    payload = asyncio.run(
        summary_ingestion.fetch_persisted_summary(
            _PersonFetchConnection(),
            str(uuid.uuid4()),
            summary_input=summary_input,
        )
    )
    assert payload is not None
    role = payload["roles_and_responsibilities"][0]
    assert role["catalog_node_id"] == person_id
    assert role["catalog_node_type_code"] == NODE_PERSON
    assert role["actor_name"] == "Priya Nair"


def test_stale_summary_is_not_returned_as_current_evidence() -> None:
    """Legacy generic summaries must yield to current body-grounded extraction."""

    class _StaleSummaryConnection:
        async def fetchrow(self, query: str, *args: Any) -> dict[str, Any]:
            assert "summary_contract_version" in query
            return {
                "korean_summary": "오래된 일반화 요약",
                "summary_contract_version": POST_SUMMARY_CONTRACT_VERSION - 1,
            }

        async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
            raise AssertionError("stale summary must be rejected before loading projections")

    payload = asyncio.run(
        summary_ingestion.fetch_persisted_summary(_StaleSummaryConnection(), str(uuid.uuid4()))
    )
    assert payload is None


class _PersonPersistConnection(_SummaryConnection):
    """Resolve one existing catalog person during the write transaction."""

    def __init__(self, events: list[Any], person_id: str) -> None:
        super().__init__(events)
        self._person_id = person_id

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        compact = " ".join(query.split())
        if compact.startswith("select person_id from cataloged_person"):
            assert "order by created_at, person_id limit 1" in compact
            assert self.in_transaction
            self._events.append(("fetchrow", compact))
            return {"person_id": self._person_id}
        return await super().fetchrow(query, *args)


def test_persist_stores_earliest_person_catalog_id(monkeypatch) -> None:
    """Write-time person lookup stores the catalog id on the role row."""

    events: list[Any] = []
    person_id = str(uuid.uuid4())
    connection = _PersonPersistConnection(events, person_id)

    async def load_candidates(conn) -> list[Any]:
        return []

    async def persist_edges(conn, post_id) -> list[Any]:
        return []

    monkeypatch.setattr(summary_ingestion, "_load_corporate_entity_candidates", load_candidates)
    monkeypatch.setattr(summary_ingestion, "persist_edges_for_post", persist_edges)

    async def current_input(*_args, **_kwargs) -> bool:
        return True

    monkeypatch.setattr(summary_ingestion, "_lock_current_summary_input", current_input)

    payload = asyncio.run(
        summary_ingestion.persist_post_summary(
            connection,
            str(uuid.uuid4()),
            PostSummary(
                korean_summary="합성 요약",
                roles_and_responsibilities=(
                    RoleResponsibility(
                        actor_name="Priya Nair",
                        responsibility="고객 측 수신",
                        actor_type_code=ACTOR_TYPE_PERSON,
                    ),
                ),
                ),
                post_body="Synthetic person evidence.",
                expected_source_body_sha256=hashlib.sha256(
                    b"Synthetic person evidence."
                ).hexdigest(),
        )
    )
    role_insert = next(
        event[1]
        for event in events
        if isinstance(event, tuple)
        and event[0] == "execute"
        and "insert into post_summary_role" in event[1]
    )
    mention_insert = next(
        event[1]
        for event in events
        if isinstance(event, tuple)
        and event[0] == "execute"
        and "insert into post_summary_person_mention" in event[1]
    )
    assert "cataloged_person_id" in role_insert
    assert "post_summary_person_mention" in mention_insert
    assert payload["korean_summary"] == "합성 요약"


def test_persist_leaves_uncataloged_person_unbound(monkeypatch) -> None:
    """A person name with no catalog row stays unbound and has no mention."""

    events: list[Any] = []
    connection = _SummaryConnection(events)

    async def load_candidates(conn) -> list[Any]:
        return []

    async def persist_edges(conn, post_id) -> list[Any]:
        return []

    monkeypatch.setattr(summary_ingestion, "_load_corporate_entity_candidates", load_candidates)
    monkeypatch.setattr(summary_ingestion, "persist_edges_for_post", persist_edges)

    async def current_input(*_args, **_kwargs) -> bool:
        return True

    monkeypatch.setattr(summary_ingestion, "_lock_current_summary_input", current_input)

    asyncio.run(
        summary_ingestion.persist_post_summary(
            connection,
            str(uuid.uuid4()),
            PostSummary(
                korean_summary="합성 요약",
                roles_and_responsibilities=(
                    RoleResponsibility(
                        actor_name="Uncataloged Person",
                        responsibility="후속",
                        actor_type_code=ACTOR_TYPE_PERSON,
                    ),
                ),
                ),
                post_body="Synthetic uncataloged person evidence.",
                expected_source_body_sha256=hashlib.sha256(
                    b"Synthetic uncataloged person evidence."
                ).hexdigest(),
        )
    )
    mention_inserts = [
        event[1]
        for event in events
        if isinstance(event, tuple)
        and event[0] == "execute"
        and "insert into post_summary_person_mention" in event[1]
    ]
    assert mention_inserts == []
    role_insert_args = next(
        event
        for event in events
        if isinstance(event, tuple)
        and event[0] == "execute"
        and "insert into post_summary_role" in event[1]
    )
    assert "catalog_unresolved_reason_code" in role_insert_args[1]


def test_role_catalog_identity_is_stored_on_the_role_row() -> None:
    """ADR 0019: fetch must not reconstruct organization identity by name."""
    root = Path(__file__).resolve().parents[1]
    fetch_source = (
        root / "backend" / "app" / "post_summary_ingestion.py"
    ).read_text(encoding="utf-8")
    initial = (root / "migrations" / "0001_initial_schema.sql").read_text(
        encoding="utf-8"
    )
    upgrade = (root / "migrations" / "0019_role_catalog_identity.sql").read_text(
        encoding="utf-8"
    )
    person_upgrade = (
        root / "migrations" / "0025_role_person_catalog_identity.sql"
    ).read_text(encoding="utf-8")
    dockerfile = (
        root / "docker" / "postgres-init" / "Dockerfile"
    ).read_text(encoding="utf-8")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    fetch_sql = fetch_source.split("async def fetch_persisted_summary", 1)[1]
    fetch_sql = fetch_sql.split("async def persist_post_summary", 1)[0]
    assert "org.entity_name = role.actor_name" not in fetch_sql
    assert "cataloged_corporate_entity_id" in fetch_sql
    assert "cataloged_person_id" in fetch_sql
    assert "cataloged_team_id" in initial
    assert "cataloged_corporate_entity_id" in upgrade
    assert "cataloged_person_id" in person_upgrade
    assert "0019_role_catalog_identity.sql" in dockerfile
    assert "0025_role_person_catalog_identity.sql" in dockerfile
    assert "ADR 0019" in changelog
    assert "ADR 0027" in changelog


def test_resolve_existing_cataloged_person_id_reports_no_catalog_entry() -> None:
    """ADR 0141: a missing person-catalog row is reason_no_catalog_entry,
    the only reason code this lookup can report -- it has no live-client
    dependency to distinguish further."""

    class _NoPersonConnection:
        async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
            assert "select person_id from cataloged_person" in query
            return None

    result = asyncio.run(
        summary_ingestion._resolve_existing_cataloged_person_id(
            _NoPersonConnection(), "Uncataloged Person"
        )
    )

    assert result == (None, "reason_no_catalog_entry")


def test_resolve_existing_cataloged_person_id_reports_no_reason_when_found() -> None:
    """A found catalog row has no unresolved reason -- it isn't unresolved."""

    person_id = str(uuid.uuid4())

    class _FoundPersonConnection:
        async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
            return {"person_id": person_id}

    result = asyncio.run(
        summary_ingestion._resolve_existing_cataloged_person_id(
            _FoundPersonConnection(), "Kim Cheolsu"
        )
    )

    assert result == (person_id, None)
