"""Synthetic cross-post Customer Master ingestion tests (ADR 0137)."""

from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import asyncpg
import pytest
from fast_mlsirm import LLMJudgeResult

import backend.app.customer_hint_ingestion as ingestion
from lineageweave.customer_identity_judgment import (
    IDENTITY_CRITERION_CODES,
    RENAME_CRITERION_CODES,
)
from lineageweave.post_evaluation import IRT_CATEGORY_COUNT
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    STATUS_UNCORROBORATED,
)
from lineageweave.tepp_client import TeppNotAvailable


class _Client:
    available = True


class _UnavailableClient:
    available = False


class _Transaction(AbstractAsyncContextManager):
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class _Judge:
    available = True

    def __init__(self, *, identity_category: int = 4, rename_category: int = 4) -> None:
        self.identity_category = identity_category
        self.rename_category = rename_category
        self.rename_calls = 0

    @staticmethod
    def _result(codes: frozenset[str], category: int) -> LLMJudgeResult:
        score = category / (IRT_CATEGORY_COUNT - 1)
        return LLMJudgeResult(
            score=score,
            accepted=score >= 0.8,
            rationale="synthetic evidence",
            criterion_scores={code: score for code in codes},
            raw_output="{}",
            orchestration_mode="auto",
            trace_step_count=2,
            usage={},
            criterion_categories={code: category for code in codes},
            category_count=IRT_CATEGORY_COUNT,
            category_method="cumulative_threshold",
        )

    def judge_identity(self, _candidate_name: str, _evidence_text: str) -> LLMJudgeResult:
        return self._result(IDENTITY_CRITERION_CODES, self.identity_category)

    def judge_rename(
        self, _previous_name: str, _candidate_name: str, _evidence_text: str
    ) -> LLMJudgeResult:
        self.rename_calls += 1
        return self._result(RENAME_CRITERION_CODES, self.rename_category)


class _Connection:
    def __init__(
        self,
        *,
        sample_rows: list[dict[str, object]] | None = None,
        binding: dict[str, object] | None = None,
        current_entity_name: str = "Northridge Grid",
        cached: dict[str, object] | None = None,
        binding_insert_entity: str | None = None,
    ) -> None:
        self.sample_rows = sample_rows or []
        self.binding = binding
        self.current_entity_name = current_entity_name
        self.cached = cached
        self.binding_insert_entity = binding_insert_entity
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.fetched: list[tuple[str, tuple[object, ...]]] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def fetch(self, query: str, *args: object):
        self.fetched.append((query, args))
        if "left(post_body" in query:
            return self.sample_rows
        if "select corporate_entity_id, entity_name from corporate_entity" in query:
            return []
        return []

    async def fetchrow(self, query: str, *args: object):
        self.fetched.append((query, args))
        if "from customer_identity_judgment judgment" in query:
            return self.cached
        if "insert into customer_identity_judgment" in query:
            return {"customer_identity_judgment_id": "judgment-id"}
        if "insert into customer_identity_binding" in query:
            return {"corporate_entity_id": self.binding_insert_entity or args[2]}
        if "from customer_identity_binding binding" in query:
            return self.binding
        if "select entity_name, created_at from corporate_entity" in query:
            return {
                "entity_name": self.current_entity_name,
                "created_at": datetime(2025, 1, 1, tzinfo=UTC),
            }
        return None

    async def execute(self, query: str, *args: object):
        self.executed.append((query, args))
        return "OK"


def _rows(count: int = 2) -> list[dict[str, object]]:
    clock = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        {
            "post_id": f"00000000-0000-0000-0000-00000000000{index}",
            "post_title": f"Synthetic visit {index}",
            "post_body": "<p>Synthetic Northridge Grid visit evidence.</p>",
            "source_customer_name": "Northridge Grid",
            "created_at": clock + timedelta(days=index),
            "updated_at": clock + timedelta(days=index, hours=1),
        }
        for index in range(1, count + 1)
    ]


def _resolution(status: str, name: str = "Northridge Grid"):
    return SimpleNamespace(
        raw_organization_name="0019999999",
        resolved_organization_name=name,
        verification_status_code=status,
        verification_evidence_url=(
            "https://evidence.example/result" if status == STATUS_CORROBORATED else None
        ),
    )


def _resolve(conn: _Connection, *, judge: _Judge | None = None):
    return ingestion.resolve_customer_hint(
        conn,
        _Client(),
        _Client(),
        "0019999999",
        source_system_code="synthetic-crm",
        authorized_corporate_entity_ids=("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",),
        identity_judge_client=judge or _Judge(),
        hierarchy_inference_client=_Client(),
    )


def test_unavailable_or_single_post_evidence_never_promotes() -> None:
    unavailable = asyncio.run(
        ingestion.resolve_customer_hint(
            _Connection(sample_rows=_rows()),
            _UnavailableClient(),
            _Client(),
            "0019999999",
            source_system_code="synthetic-crm",
            authorized_corporate_entity_ids=("scope",),
            identity_judge_client=_Judge(),
        )
    )
    single = asyncio.run(_resolve(_Connection(sample_rows=_rows(1))))
    assert unavailable is None
    assert single is None


def test_evidence_clock_and_absent_source_context_are_explicit() -> None:
    naive = datetime(2026, 1, 1)  # noqa: DTZ001 - deliberate legacy naive-clock case.
    assert ingestion._iso8601(naive).endswith("+00:00")
    with pytest.raises(TypeError, match="datetime"):
        ingestion._iso8601("2026-01-01")
    context = ingestion._judge_context(
        [
            {
                "post_id": "post",
                "source_customer_name": None,
                "created_at": "created",
                "updated_at": "updated",
                "post_title": "title",
                "excerpt": "body",
            }
        ],
        None,
        "CODE",
    )
    assert "source_system_code=(source system absent)" in context
    assert "source_customer_name=(absent)" in context


def test_tepp_orders_opaque_post_events_and_falls_back_when_unavailable() -> None:
    records = ingestion._evidence_records(_rows())

    class _Tepp:
        def temporal_context(self, request):
            return {"source_post_ids": [event.source_post_id for event in reversed(request.events)]}

    class _UnavailableTepp:
        def temporal_context(self, _request):
            raise TeppNotAvailable("synthetic outage")

    ordered, source = asyncio.run(
        ingestion._temporally_order_records(records, _Tepp(), "crm", "CODE")
    )
    fallback, fallback_source = asyncio.run(
        ingestion._temporally_order_records(records, _UnavailableTepp(), "crm", "CODE")
    )

    assert [row["post_id"] for row in ordered] == [row["post_id"] for row in reversed(records)]
    assert source == "tepp"
    assert [row["post_id"] for row in fallback] == [row["post_id"] for row in records]
    assert fallback_source == "source_timestamp"


def test_uncorroborated_or_weak_judgment_persists_abstention_without_binding(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_UNCORROBORATED),
    )
    conn = _Connection(sample_rows=_rows())
    result = asyncio.run(_resolve(conn, judge=_Judge(identity_category=2)))

    assert result is None
    assert any("insert into customer_identity_judgment" in query for query, _ in conn.fetched)
    assert all(
        "insert into customer_identity_binding" not in query
        for query, _ in (*conn.fetched, *conn.executed)
    )

    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_CORROBORATED),
    )
    weak_conn = _Connection(sample_rows=_rows())
    assert asyncio.run(_resolve(weak_conn, judge=_Judge(identity_category=2))) is None


def test_strong_repeated_evidence_promotes_without_rewriting_authorization_scope(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_CORROBORATED),
    )

    async def catalog(*_args, **_kwargs):
        return "new-entity-id"

    projected: list[str] = []

    async def project(_conn, post_id):
        projected.append(post_id)
        return []

    monkeypatch.setattr(ingestion, "_catalog_entity", catalog)
    monkeypatch.setattr(ingestion, "persist_edges_for_post", project)
    conn = _Connection(sample_rows=_rows())
    result = asyncio.run(_resolve(conn))

    assert result == {
        "corporate_entity_id": "new-entity-id",
        "entity_name": "Northridge Grid",
        "linked_post_count": 2,
        "verification_evidence_url": "https://evidence.example/result",
        "customer_identity_judgment_id": "judgment-id",
        "resolution_status": "customer_identity_promoted",
        "cached": False,
    }
    assert len(projected) == 2
    assert any("insert into customer_identity_binding" in query for query, _ in conn.fetched)
    assert any("insert into post_customer_identity_mention" in query for query, _ in conn.executed)
    assert all("update source_post" not in query for query, _ in conn.executed)
    evidence_query, evidence_args = next(
        item for item in conn.fetched if "left(post_body" in item[0]
    )
    assert "source_system_code is not distinct from $2" in evidence_query
    assert evidence_args[1] == "synthetic-crm"


def test_resolution_or_catalog_abstention_never_creates_a_binding(monkeypatch) -> None:
    monkeypatch.setattr(ingestion, "resolve_and_verify_organization_name", lambda *_args: None)
    assert asyncio.run(_resolve(_Connection(sample_rows=_rows()))) is None

    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_CORROBORATED),
    )

    async def no_catalog(*_args, **_kwargs):
        return None

    monkeypatch.setattr(ingestion, "_catalog_entity", no_catalog)
    conn = _Connection(sample_rows=_rows())
    assert asyncio.run(_resolve(conn)) is None
    assert all(
        "insert into customer_identity_binding" not in query
        for query, _ in (*conn.fetched, *conn.executed)
    )


def test_catalog_entity_reuses_the_existing_resolution_path(monkeypatch) -> None:
    conn = _Connection()
    assert asyncio.run(
        ingestion._catalog_entity(conn, "Synthetic Grid", "context", None, _Client())
    ) is None
    seen: dict[str, object] = {}

    async def catalog(_conn, name, context, inference, verification, candidates):
        seen.update(name=name, context=context, candidates=candidates)
        return "entity"

    monkeypatch.setattr(ingestion, "get_or_create_corporate_entity", catalog)
    assert asyncio.run(
        ingestion._catalog_entity(conn, "Synthetic Grid", "context", _Client(), _Client())
    ) == "entity"
    assert seen["name"] == "Synthetic Grid"


def test_different_name_is_alias_until_strict_rename_judge_passes(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_CORROBORATED, "Northridge Energy"),
    )

    async def project(*_args):
        return []

    monkeypatch.setattr(ingestion, "persist_edges_for_post", project)
    binding = {
        "corporate_entity_id": "existing-entity-id",
        "entity_name": "Northridge Grid",
    }
    conn = _Connection(
        sample_rows=_rows(), binding=binding, current_entity_name="Northridge Grid"
    )
    judge = _Judge(rename_category=3)
    result = asyncio.run(_resolve(conn, judge=judge))

    assert result["entity_name"] == "Northridge Grid"
    assert judge.rename_calls == 1
    assert any("'entity_name_alternate'" in query for query, _ in conn.executed)
    assert all("update corporate_entity set entity_name" not in query for query, _ in conn.executed)


def test_concurrent_existing_binding_wins_over_a_new_catalog_candidate(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_CORROBORATED),
    )

    async def catalog(*_args, **_kwargs):
        return "concurrent-candidate"

    async def project(*_args):
        return []

    monkeypatch.setattr(ingestion, "_catalog_entity", catalog)
    monkeypatch.setattr(ingestion, "persist_edges_for_post", project)
    conn = _Connection(
        sample_rows=_rows(),
        binding_insert_entity="stable-existing-entity",
    )

    result = asyncio.run(_resolve(conn))

    assert result["corporate_entity_id"] == "stable-existing-entity"
    mention_args = [
        args
        for query, args in conn.executed
        if "insert into post_customer_identity_mention" in query
    ]
    assert {args[1] for args in mention_args} == {"stable-existing-entity"}


def test_strict_formal_rename_replaces_preferred_name_and_keeps_history(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_CORROBORATED, "Northridge Energy"),
    )

    async def project(*_args):
        return []

    monkeypatch.setattr(ingestion, "persist_edges_for_post", project)
    conn = _Connection(
        sample_rows=_rows(),
        binding={
            "corporate_entity_id": "existing-entity-id",
            "entity_name": "Northridge Grid",
        },
        current_entity_name="Northridge Grid",
    )
    result = asyncio.run(_resolve(conn, judge=_Judge(rename_category=4)))

    assert result["entity_name"] == "Northridge Energy"
    assert any("name_role_code = 'entity_name_former'" in query for query, _ in conn.executed)
    assert any("update corporate_entity set entity_name" in query for query, _ in conn.executed)
    assert any("'entity_name_preferred'" in query for query, _ in conn.executed)


def test_unchanged_evidence_reuses_cached_promotion_without_llm(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: (_ for _ in ()).throw(AssertionError("LLM must not run")),
    )
    conn = _Connection(
        sample_rows=_rows(),
        cached={
            "customer_identity_judgment_id": "cached-judgment",
            "corporate_entity_id": "cached-entity",
            "entity_name": "Northridge Grid",
            "distinct_post_count": 2,
            "verification_evidence_url": "https://evidence.example/result",
        },
    )
    result = asyncio.run(_resolve(conn))

    assert result["cached"] is True
    assert result["corporate_entity_id"] == "cached-entity"


def test_reconcile_deduplicates_imported_keys_and_isolates_provider_failures(
    monkeypatch,
) -> None:
    seen: list[tuple[str | None, str]] = []

    async def resolve(_conn, _resolution_client, _verification_client, hint_code: str, **kwargs):
        key = (kwargs["source_system_code"], hint_code)
        seen.append(key)
        if hint_code == "FAIL":
            raise OSError("synthetic provider outage")
        return {"resolution_status": "customer_identity_promoted"}

    monkeypatch.setattr(ingestion, "resolve_customer_hint", resolve)
    result = asyncio.run(
        ingestion.reconcile_customer_hints(
            _Connection(),
            _Client(),
            _Client(),
            (("crm", "PROMOTE"), ("crm", "PROMOTE"), ("crm", "FAIL")),
            authorized_corporate_entity_ids=("scope",),
            identity_judge_client=_Judge(),
            hierarchy_inference_client=_Client(),
        )
    )

    assert seen == [("crm", "FAIL"), ("crm", "PROMOTE")]
    assert result == {"candidates": 2, "promoted": 1, "unresolved": 0, "unavailable": 1}


def test_reconcile_reports_unavailable_channels_without_attempting_work(monkeypatch) -> None:
    async def unexpected(*_args, **_kwargs):
        raise AssertionError("unavailable channel must fail closed")

    monkeypatch.setattr(ingestion, "resolve_customer_hint", unexpected)
    result = asyncio.run(
        ingestion.reconcile_customer_hints(
            _Connection(),
            _UnavailableClient(),
            _Client(),
            (("crm", "ONE"),),
            authorized_corporate_entity_ids=("scope",),
            identity_judge_client=_Judge(),
            hierarchy_inference_client=_Client(),
        )
    )

    assert result == {"candidates": 1, "promoted": 0, "unresolved": 0, "unavailable": 1}


def test_reconcile_does_not_swallow_database_failures(monkeypatch) -> None:
    async def fail(*_args, **_kwargs):
        raise asyncpg.PostgresError("synthetic database failure")

    monkeypatch.setattr(ingestion, "resolve_customer_hint", fail)
    with pytest.raises(asyncpg.PostgresError, match="synthetic database failure"):
        asyncio.run(
            ingestion.reconcile_customer_hints(
                _Connection(),
                _Client(),
                _Client(),
                (("crm", "ONE"),),
                authorized_corporate_entity_ids=("scope",),
                identity_judge_client=_Judge(),
                hierarchy_inference_client=_Client(),
            )
        )
