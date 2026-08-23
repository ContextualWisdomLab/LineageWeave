"""Unit tests for source_post → Record mapping used by lineage rebuild."""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone

import pytest

from backend.app import lineage_ingestion
from backend.app.lineage_ingestion import (
    rebuild_lineage,
    reconstruct_group_key,
    records_from_source_posts,
    visible_lineage_graph,
)
from lineageweave.adjudication_client import ContextualOrchestratorAdjudicationClient
from lineageweave.fixtures import sample_records
from lineageweave.http_client import HttpClientError
from lineageweave.lineage_persistence import lineage_edge_specs
from lineageweave.models import Edge


class _Transaction:
    """Record the transaction boundary used by a synthetic connection."""

    def __init__(self, events: list[str]) -> None:
        """Store the shared event sequence."""
        self._events = events

    async def __aenter__(self) -> "_Transaction":
        """Record transaction entry."""
        self._events.append("transaction_enter")
        return self

    async def __aexit__(self, *_args: object) -> bool:
        """Record transaction exit without suppressing failures."""
        self._events.append("transaction_exit")
        return False


class _RebuildConnection:
    """Minimal asyncpg-shaped connection for corpus rebuild tests."""

    def __init__(
        self,
        rows: list[dict[str, object]] | None = None,
        *,
        snapshots: list[list[dict[str, object]]] | None = None,
    ) -> None:
        """Initialize synthetic rows and an observable operation sequence."""
        self.rows = rows or []
        self.snapshots = snapshots or []
        self.fetch_count = 0
        self.events: list[str] = []
        self.executed: list[str] = []

    async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
        """Return synthetic source rows while recording the read."""
        del query, args
        self.events.append("fetch")
        if self.snapshots:
            index = min(self.fetch_count, len(self.snapshots) - 1)
            self.fetch_count += 1
            return self.snapshots[index]
        return self.rows

    async def execute(self, query: str, *args: object) -> str:
        """Record a synthetic projection write."""
        del args
        compact = " ".join(query.split())
        if "pg_advisory_unlock" in compact:
            self.events.append("rebuild_lock_release")
        elif "pg_advisory_lock" in compact:
            self.events.append("rebuild_lock_acquire")
        elif compact == "lock table source_post in share mode":
            self.events.append("source_lock")
        else:
            self.events.append("execute")
        self.executed.append(query)
        return "OK"

    def transaction(self) -> _Transaction:
        """Return the observable transaction context manager."""
        return _Transaction(self.events)


def test_records_use_persisted_thread_keys_not_process_unit_or_voc_type() -> None:
    rows = [
        {
            "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "process_unit_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "corporate_entity_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "post_title": "Pricing renegotiation follow-up",
            "voc_type_code": "voc",
            "thread_group_key": "A-100",
            "secondary_grouping_key": "proj-alpha",
            "created_at": datetime(2026, 1, 6, tzinfo=timezone.utc),
        }
    ]
    records = records_from_source_posts(rows)
    assert records[0].group_key == "A-100"
    assert records[0].secondary_key == "proj-alpha"
    assert records[0].occurred_at.tzinfo is None


def test_records_fall_back_to_corporate_entity_when_thread_keys_are_empty() -> None:
    rows = [
        {
            "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "process_unit_id": None,
            "corporate_entity_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "post_title": "Corp-only post",
            "voc_type_code": "vom",
            "thread_group_key": "",
            "secondary_grouping_key": "",
            "created_at": datetime(2026, 2, 1),
        }
    ]
    records = records_from_source_posts(rows)
    assert records[0].group_key == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert records[0].secondary_key == ""
    assert records[0].label == "Corp-only post"


def test_display_group_matches_reconstruct_group_key() -> None:
    """The DAG's group field is reconstruct's key, not voc type or PU."""
    a100 = {
        "process_unit_id": "shared-pu",
        "corporate_entity_id": "shared-corp",
        "thread_group_key": "A-100",
    }
    ungrouped = {
        "process_unit_id": "shared-pu",
        "corporate_entity_id": "shared-corp",
        "thread_group_key": "",
    }
    assert reconstruct_group_key(a100) == "A-100"
    assert reconstruct_group_key(ungrouped) == "shared-pu"


def test_seed_shaped_rows_rebuild_to_the_designed_a100_fork() -> None:
    """The mapping rebuild uses: fixture group/secondary + occurred_at.

    This is the same column set seed writes. If voc_type or process_unit
    were used instead, A-100/B-200 collapse and the rec-002 fork is lost.
    """
    rows = []
    for rec in sample_records():
        rows.append(
            {
                "post_id": rec.record_id,
                "process_unit_id": "shared-pu",
                "corporate_entity_id": "shared-corp",
                "post_title": rec.label,
                "voc_type_code": "voc" if rec.secondary_key else "vom",
                "thread_group_key": rec.group_key,
                "secondary_grouping_key": rec.secondary_key,
                "created_at": rec.occurred_at,
            }
        )
    edges = lineage_edge_specs(records_from_source_posts(rows))
    pairs = {(edge.parent_id, edge.child_id) for edge in edges}
    assert ("rec-002", "rec-003") in pairs
    assert ("rec-002", "rec-004") in pairs
    assert "rec-006" not in {edge.child_id for edge in edges}


def test_focused_lineage_graph_includes_a_post_outside_landing_limit() -> None:
    class FakeConnection:
        posts = [
            {
                "post_id": "post-a",
                "post_title": "A",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-a",
                "created_at": datetime(2026, 1, 1),
            },
            {
                "post_id": "post-b",
                "post_title": "B",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-a",
                "created_at": datetime(2026, 1, 2),
            },
            {
                "post_id": "post-c",
                "post_title": "C",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-c",
                "created_at": datetime(2026, 1, 3),
            },
        ]
        edges = [
            {"parent_post_id": "post-a", "child_post_id": "post-b", "fused_score": 0.8}
        ]

        async def fetch(self, query: str):
            return self.edges if "post_lineage_edge" in query else self.posts

    connection = FakeConnection()
    landing = asyncio.run(visible_lineage_graph(connection, lambda row: True, limit=1))
    focused = asyncio.run(
        visible_lineage_graph(connection, lambda row: True, limit=1, focus_post_id="post-a")
    )
    isolated = asyncio.run(
        visible_lineage_graph(connection, lambda row: True, limit=1, focus_post_id="post-c")
    )

    assert [node["id"] for node in landing["nodes"]] == ["post-c"]
    assert {node["id"] for node in focused["nodes"]} == {"post-a", "post-b"}
    assert len(focused["edges"]) == 1
    assert focused["truncated"] is False
    assert isolated == {"nodes": [], "edges": [], "truncated": False}


def test_focused_lineage_graph_terminates_on_a_corrupted_cycle() -> None:
    """Defensive traversal must not loop if persisted edges contain a cycle."""

    class CyclicConnection:
        """Expose a synthetic three-post cycle instead of a valid tree."""

        posts = [
            {
                "post_id": post_id,
                "post_title": f"Synthetic post {post_id}",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "synthetic-corp",
                "process_unit_id": "synthetic-pu",
                "thread_group_key": "synthetic-thread",
                "created_at": datetime(2026, 1, day, tzinfo=timezone.utc),
            }
            for day, post_id in enumerate(("post-a", "post-b", "post-c"), start=1)
        ]
        edges = [
            {"parent_post_id": "post-a", "child_post_id": "post-b", "fused_score": 0.8},
            {"parent_post_id": "post-b", "child_post_id": "post-c", "fused_score": 0.8},
            {"parent_post_id": "post-c", "child_post_id": "post-a", "fused_score": 0.8},
        ]

        async def fetch(self, query: str) -> list[dict[str, object]]:
            """Return the requested synthetic projection."""
            return self.edges if "post_lineage_edge" in query else self.posts

    focused = asyncio.run(
        visible_lineage_graph(
            CyclicConnection(), lambda row: True, focus_post_id="post-a"
        )
    )

    assert {node["id"] for node in focused["nodes"]} == {"post-a", "post-b", "post-c"}
    assert len(focused["edges"]) == 3


def test_rebuild_lineage_passes_the_adjudication_client_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live bug (2026-08-22): rebuild_lineage() called lineage_edge_specs()
    without llm=, so the corpus-wide rebuild (POST /api/lineage/rebuild and
    scripts/import_postgresql_posts.py) silently ran reconstruct() on the
    weaker 3-channel fallback -- the highest-weighted channel
    (DEFAULT_CHANNEL_WEIGHTS, ADR 0064) never actually reasoned about any
    real corpus. Assert the caller-supplied client reaches
    lineage_edge_specs unchanged, without depending on reconstruct()'s own
    decision about when to actually invoke it.
    """
    captured: dict[str, object] = {}

    def fake_lineage_edge_specs(records, *, llm=None):
        captured["llm"] = llm
        return []

    monkeypatch.setattr(
        "backend.app.lineage_ingestion.lineage_edge_specs", fake_lineage_edge_specs
    )

    sentinel_client = object()
    asyncio.run(rebuild_lineage(_RebuildConnection(), adjudication_client=sentinel_client))
    assert captured["llm"] is sentinel_client


def test_rebuild_lineage_defaults_to_no_adjudication_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default stays None (lineage_edge_specs/reconstruct's own
    documented fallback) -- this only guards that rebuild_lineage's new
    keyword argument doesn't silently require a client everywhere.
    """
    captured: dict[str, object] = {"llm": "unset"}

    def fake_lineage_edge_specs(records, *, llm=None):
        captured["llm"] = llm
        return []

    monkeypatch.setattr(
        "backend.app.lineage_ingestion.lineage_edge_specs", fake_lineage_edge_specs
    )

    asyncio.run(rebuild_lineage(_RebuildConnection()))
    assert captured["llm"] is None


def test_rebuild_lineage_keeps_blocking_adjudication_outside_event_loop_and_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A slow synchronous provider must not stall unrelated async API work.

    The synthetic provider blocks until the event-loop coroutine releases it.
    This would time out if reconstruction ran directly on the event-loop
    thread. The observable connection also proves the write transaction starts
    only after provider work completes.
    """
    provider_entered = threading.Event()
    provider_release = threading.Event()
    connection = _RebuildConnection()

    def blocking_lineage_edge_specs(records, *, llm=None):
        """Model a synchronous contextual-orchestrator request."""
        del records, llm
        connection.events.append("reconstruct")
        provider_entered.set()
        assert provider_release.wait(timeout=2), (
            "event loop could not release provider work"
        )
        return [Edge("parent-post", "child-post", 0.8, {})]

    monkeypatch.setattr(
        "backend.app.lineage_ingestion.lineage_edge_specs", blocking_lineage_edge_specs
    )

    async def run_rebuild() -> list[Edge]:
        """Release provider work from the still-responsive event loop."""
        task = asyncio.create_task(rebuild_lineage(connection))
        for _ in range(100):
            if provider_entered.is_set():
                break
            await asyncio.sleep(0)
        assert provider_entered.is_set()
        assert "transaction_enter" not in connection.events
        provider_release.set()
        return await task

    edges = asyncio.run(run_rebuild())

    assert [(edge.parent_id, edge.child_id) for edge in edges] == [
        ("parent-post", "child-post")
    ]
    assert connection.events == [
        "rebuild_lock_acquire",
        "fetch",
        "reconstruct",
        "transaction_enter",
        "source_lock",
        "fetch",
        "execute",
        "execute",
        "transaction_exit",
        "rebuild_lock_release",
    ]


def _synthetic_source_row(title: str) -> dict[str, object]:
    """Build one non-identifying source row for rebuild concurrency tests."""
    return {
        "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "process_unit_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "corporate_entity_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "post_title": title,
        "voc_type_code": "voc",
        "thread_group_key": "synthetic-thread",
        "secondary_grouping_key": "synthetic-project",
        "created_at": datetime(2026, 1, 6, tzinfo=timezone.utc),
    }


def test_rebuild_lineage_recomputes_a_source_snapshot_changed_during_adjudication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only edges calculated from the locked current source may be published."""
    before = [_synthetic_source_row("Synthetic schedule draft")]
    after = [_synthetic_source_row("Synthetic schedule approved")]
    connection = _RebuildConnection(
        snapshots=[before, after, after, after]
    )
    reconstructed_titles: list[list[str]] = []

    def record_reconstruction(records, *, llm=None):
        """Record which synthetic source version reached reconstruction."""
        del llm
        reconstructed_titles.append([record.label for record in records])
        return []

    monkeypatch.setattr(lineage_ingestion, "lineage_edge_specs", record_reconstruction)

    assert asyncio.run(rebuild_lineage(connection)) == []
    assert reconstructed_titles == [
        ["Synthetic schedule draft"],
        ["Synthetic schedule approved"],
    ]
    assert sum("delete from post_lineage_edge" in query for query in connection.executed) == 1
    assert connection.events[0] == "rebuild_lock_acquire"
    assert connection.events[-1] == "rebuild_lock_release"


def test_rebuild_lineage_keeps_prior_projection_after_bounded_snapshot_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Continuous source changes fail retryably without deleting stored edges."""
    snapshots = [
        [_synthetic_source_row(f"Synthetic source version {version}")]
        for version in range(1, 7)
    ]
    connection = _RebuildConnection(snapshots=snapshots)
    monkeypatch.setattr(lineage_ingestion, "lineage_edge_specs", lambda *_args, **_kwargs: [])

    with pytest.raises(
        lineage_ingestion.LineageSourceChangedError,
        match="changed during three reconstruction attempts",
    ):
        asyncio.run(rebuild_lineage(connection))

    assert all("delete from post_lineage_edge" not in query for query in connection.executed)
    assert connection.events[0] == "rebuild_lock_acquire"
    assert connection.events[-1] == "rebuild_lock_release"


@pytest.mark.parametrize(
    ("failure", "expected_next_action"),
    [
        (
            HttpClientError("synthetic adjudication response was malformed"),
            "Retry after the orchestrator is available.",
        ),
        (
            lineage_ingestion.LineageSourceChangedError("synthetic source changed"),
            "Retry after the current ingestion finishes.",
        ),
    ],
)
def test_rebuild_endpoint_reports_retryable_unavailability(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    expected_next_action: str,
) -> None:
    """A temporary rebuild boundary failure is a retryable actionable 503."""
    from fastapi import HTTPException

    from backend.app import main as api

    class Account:
        """Synthetic administrator accepted by the route guard."""

        def has_permission(self, _permission: str) -> bool:
            """Grant the one permission required by this route."""
            return True

    class Acquire:
        """Yield the synthetic connection through the pool contract."""

        async def __aenter__(self) -> _RebuildConnection:
            """Return a connection for the route call."""
            return _RebuildConnection()

        async def __aexit__(self, *_args: object) -> bool:
            """Leave the acquisition context without suppressing errors."""
            return False

    class Pool:
        """Minimal pool exposing one acquisition context."""

        def acquire(self) -> Acquire:
            """Return the synthetic acquisition context."""
            return Acquire()

    async def unavailable_rebuild(*_args: object, **_kwargs: object) -> list[Edge]:
        """Model a temporary provider or source-snapshot failure."""
        raise failure

    monkeypatch.setattr(api, "rebuild_lineage", unavailable_rebuild)
    monkeypatch.setattr(api, "_adjudication_client", object)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(api.rebuild_lineage_graph(account=Account(), pool=Pool()))

    assert caught.value.status_code == 503
    assert caught.value.detail.endswith(expected_next_action)


def test_analysis_run_start_reports_retryable_adjudication_unavailability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The run-start API maps an invalid provider reply to an actionable 503."""
    from fastapi import HTTPException

    from backend.app import main as api

    class Account:
        """Synthetic reader with one authorized corporate scope."""

        user_account_id = "synthetic-account"
        corporate_entity_ids = ("synthetic-corporate-entity",)

        @staticmethod
        def has_permission(_permission: str) -> bool:
            """Grant the permission required by the analysis-run route."""
            return True

    class Acquire:
        """Yield a synthetic connection through the pool contract."""

        async def __aenter__(self) -> _RebuildConnection:
            """Return one connection for either route transaction."""
            return _RebuildConnection()

        async def __aexit__(self, *_args: object) -> bool:
            """Leave acquisition without suppressing the provider error."""
            return False

    class Pool:
        """Expose a fresh synthetic acquisition context per transaction."""

        @staticmethod
        def acquire() -> Acquire:
            """Create an acquisition context for the route."""
            return Acquire()

    async def enqueue(*_args: object, **_kwargs: object) -> dict[str, object]:
        """Return a durable synthetic queued run with no stream delivery."""
        return {
            "status_code": "analysis_status_running",
            "run_kind_code": "analysis_kind_lineage",
            "outbox_request_sha256": None,
        }

    async def unavailable_delivery(
        *_args: object, **_kwargs: object
    ) -> dict[str, object]:
        """Model an adjudication response that violates the score contract."""
        raise HttpClientError("synthetic adjudication response was malformed")

    monkeypatch.setattr(api, "enqueue_pending_analysis_run", enqueue)
    monkeypatch.setattr(api, "deliver_queued_analysis_run", unavailable_delivery)
    monkeypatch.setattr(api, "_adjudication_client", object)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            api.start_analysis_run(
                "synthetic-analysis-run",
                account=Account(),
                pool=Pool(),
                valkey=object(),  # type: ignore[arg-type]
            )
        )

    assert caught.value.status_code == 503
    assert caught.value.detail.endswith(
        "Retry this run after the orchestrator is available."
    )


def test_rebuild_lineage_fails_closed_when_adjudication_cannot_be_parsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CodeRabbit-flagged data-integrity bug (PR #434): a genuine judge()
    parse failure must abort the corpus-wide rebuild before any
    post_lineage_edge write, instead of quietly persisting an edge fused
    from a fabricated "definitely unrelated" 0.0. Exercises the real
    ContextualOrchestratorAdjudicationClient -> reconstruct -> rebuild_lineage
    path end to end, not a stub.
    """
    monkeypatch.setattr(
        "lineageweave.adjudication_client.post_json",
        lambda *args, **kwargs: {"choices": [{"message": {"content": "no number in this reply"}}]},
    )
    client = ContextualOrchestratorAdjudicationClient(
        base_url="http://orchestrator:8000", api_key="synthetic-token"
    )

    rows = [
        {
            "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "post_title": "Initial inquiry",
            "voc_type_code": "voc",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "corporate_entity_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "process_unit_id": None,
            "thread_group_key": "A-100",
            "secondary_grouping_key": "",
        },
        {
            "post_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "post_title": "Follow-up on inquiry",
            "voc_type_code": "voc",
            "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "corporate_entity_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "process_unit_id": None,
            "thread_group_key": "A-100",
            "secondary_grouping_key": "",
        },
    ]

    connection = _RebuildConnection(rows)
    with pytest.raises(HttpClientError):
        asyncio.run(rebuild_lineage(connection, adjudication_client=client))

    # No delete-then-insert of post_lineage_edge happened: the failure was
    # raised while computing edges, strictly before persist_lineage_edges runs.
    assert all(
        "post_lineage_edge" not in query for query in connection.executed
    )
