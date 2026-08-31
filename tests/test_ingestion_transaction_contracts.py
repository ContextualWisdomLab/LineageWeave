"""Regression contracts for ingestion transactions and review documentation."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from backend.app import corporate_entity_ingestion as corporate_ingestion
from backend.app import keyman_ingestion
from backend.app import post_summary_ingestion as summary_ingestion
from lineageweave.corporate_hierarchy_inference import HierarchyProposal
from lineageweave.keyman_extraction import OUR_SIDE, PersonMention
from lineageweave.knowledge_graph import NODE_PERSON
from lineageweave.post_summary import (
    ACTOR_TYPE_ORGANIZATION,
    ACTOR_TYPE_PERSON,
    ACTOR_TYPE_TEAM,
    PostSummary,
    POST_SUMMARY_CONTRACT_VERSION,
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
        if compact.startswith("select korean_summary, summary_contract_version from post_summary_result"):
            assert not self.in_transaction
            return {
                "korean_summary": "합성 요약",
                "summary_contract_version": POST_SUMMARY_CONTRACT_VERSION,
            }
        if compact.startswith("select person_id from cataloged_person"):
            assert self.in_transaction
            return None
        raise AssertionError(f"unexpected fetchrow query: {compact}")

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        compact = " ".join(query.split())
        self._events.append(("fetch", compact))
        assert not self.in_transaction
        if "from post_summary_action" in compact:
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
                    "responsibility": "도면 검토",
                    "actor_type_code": ACTOR_TYPE_TEAM,
                    "affiliated_organization_name": "Synthetic Energy",
                    "cataloged_team_id": None,
                    "cataloged_corporate_entity_id": None,
                    "cataloged_person_id": None,
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
        "select 1 from source_post",
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
        **_kwargs,
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
    role_insert = next(
        event[1]
        for event in events
        if isinstance(event, tuple)
        and event[0] == "execute"
        and "insert into post_summary_role" in event[1]
    )
    assert "cataloged_corporate_entity_id" in role_insert
    assert "cataloged_person_id" in role_insert
    assert resolve_index < enter_index < mention_index < exit_index


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

    async def resolve_name(conn, resolution_client, verification_client, organization_name, post_body) -> str:
        events.append(("organization_resolve", conn.in_transaction))
        assert not conn.in_transaction
        return "Aurora Grid Power"

    async def resolve_organization(
        conn,
        organization_name,
        context_text,
        inference_client,
        verification_client,
        candidates,
        **_kwargs,
    ) -> str:
        events.append(("organization_create", conn.in_transaction))
        assert not conn.in_transaction
        return corporate_entity_id

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

    monkeypatch.setattr(keyman_ingestion, "resolve_organization_name", resolve_name)
    monkeypatch.setattr(keyman_ingestion, "get_or_create_corporate_entity", resolve_organization)

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
    events: list[Any] = []

    class _PersonFetchConnection:
        """Return one stored person catalog id without a live database."""

        async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
            compact = " ".join(query.split())
            events.append(("fetchrow", compact))
            if compact.startswith("select korean_summary, summary_contract_version from post_summary_result"):
                return {
                    "korean_summary": "합성 요약",
                    "summary_contract_version": POST_SUMMARY_CONTRACT_VERSION,
                }
            raise AssertionError(f"unexpected fetchrow query: {compact}")

        async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
            compact = " ".join(query.split())
            events.append(("fetch", compact))
            if "from post_summary_action" in compact:
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
                        "responsibility": "고객 측 수신",
                        "actor_type_code": ACTOR_TYPE_PERSON,
                        "affiliated_organization_name": "Northridge Grid",
                        "cataloged_team_id": None,
                        "cataloged_corporate_entity_id": None,
                        "cataloged_person_id": person_id,
                    }
                ]
            raise AssertionError(f"unexpected fetch query: {compact}")

    payload = asyncio.run(
        summary_ingestion.fetch_persisted_summary(_PersonFetchConnection(), str(uuid.uuid4()))
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
