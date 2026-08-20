from __future__ import annotations

from typing import Any

import pytest

from backend.app import post_chat_ingestion as ingestion
from lineageweave.claim_verification import GlobalAskSourceDocument

_CANDIDATE_POST_ID = "11111111-1111-1111-1111-111111111111"
_UNRELATED_POST_ID = "22222222-2222-2222-2222-222222222222"


def _post_row(post_id: str, *, title: str = "Apollo", visibility: str = "public") -> dict[str, Any]:
    return {
        "post_id": post_id,
        "post_title": title,
        "post_body": f"Body for {title}",
        "visibility_code": visibility,
        "corporate_entity_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "source_system_code": None,
        "source_record_key": None,
        "source_author_code": None,
        "source_author_name": None,
        "source_company_code": None,
        "source_company_name": None,
        "source_process_unit_code": None,
        "source_process_unit_name": None,
        "source_sales_pool_code": None,
        "source_sales_pool_name": None,
        "source_customer_code": None,
        "source_customer_name": None,
        "source_project_code": None,
        "source_project_name": None,
    }


class _FakeConnection:
    def __init__(self, *, lexical_rows: list[dict[str, Any]], final_rows: list[dict[str, Any]]) -> None:
        self.lexical_rows = lexical_rows
        self.final_rows = final_rows
        self.final_query_calls = 0

    async def fetch(self, query: str, *arguments: Any) -> list[dict[str, Any]]:
        if "select post_id, matched_in" in query:
            return self.lexical_rows
        if "select child_post_id as other_id" in query:
            return []
        if "matched_organization_label" in query:
            # The integration fixture has no corroborated label rows. Keep
            # the new post-ABAC evidence lookup explicit so this double tracks
            # the production query contract instead of rejecting it.
            return []
        if "select post_id, post_title, post_body" in query:
            self.final_query_calls += 1
            return self.final_rows
        raise AssertionError(f"unexpected query: {query}")


async def _no_semantic_facts(_conn: Any, post_ids: list[str]) -> dict[str, tuple[str, ...]]:
    return {
        post_id: ("project: Apollo | evidence: Public launch",)
        for post_id in post_ids
    }


async def _public_graph_facts(_conn: Any, post_ids: list[str]) -> tuple[str, ...]:
    if not post_ids:
        return ()
    return (
        'node_team "Apollo" --edge_team_affiliation--> node_organization "Acme" '
        f"[evidence_post_id={_CANDIDATE_POST_ID}]",
    )


async def _normalized_body(body: str, _vision_client: Any) -> str:
    return body


@pytest.mark.anyio
async def test_semantic_nomination_returns_only_relevant_authorized_egress_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic_calls: list[str | None] = []
    egress_calls: list[str] = []

    async def semantic_candidates(
        _conn: Any,
        question: str | None,
        *,
        maximum_candidates: int = 128,
    ) -> list[str]:
        semantic_calls.append(question)
        assert maximum_candidates == 128
        return [_CANDIDATE_POST_ID]

    def public_claims(
        row: dict[str, Any],
        semantic_facts: tuple[str, ...],
        graph_facts: tuple[str, ...],
        public_post_ids: frozenset[str],
    ) -> tuple[str, ...]:
        egress_calls.append(str(row["post_id"]))
        assert semantic_facts == ("project: Apollo | evidence: Public launch",)
        assert graph_facts
        assert _CANDIDATE_POST_ID in public_post_ids
        return semantic_facts

    monkeypatch.setattr(
        ingestion,
        "semantic_candidate_post_ids",
        semantic_candidates,
        raising=False,
    )
    monkeypatch.setattr(
        ingestion,
        "public_external_claim_facts",
        public_claims,
        raising=False,
    )
    monkeypatch.setattr(
        ingestion,
        "GlobalAskSourceDocument",
        GlobalAskSourceDocument,
        raising=False,
    )
    monkeypatch.setattr(ingestion, "_semantic_facts_for_posts", _no_semantic_facts)
    monkeypatch.setattr(ingestion, "_graph_facts_for_posts", _public_graph_facts)
    monkeypatch.setattr(ingestion, "_normalize_post_body_text", _normalized_body)

    connection = _FakeConnection(
        lexical_rows=[],
        final_rows=[
            _post_row(_CANDIDATE_POST_ID),
            _post_row(_UNRELATED_POST_ID, title="Unrelated recent post"),
        ],
    )
    seen_by_abac: list[str] = []

    def can_see_post(row: dict[str, Any]) -> bool:
        seen_by_abac.append(str(row["post_id"]))
        return True

    sources = await ingestion.gather_global_chat_sources(
        connection,
        can_see_post,
        question="Apollo responsibility",
        limit=4,
    )

    assert semantic_calls == ["Apollo responsibility"]
    assert [source.post_id for source in sources] == [_CANDIDATE_POST_ID]
    assert isinstance(sources[0], GlobalAskSourceDocument)
    assert sources[0].external_claim_facts == (
        "project: Apollo | evidence: Public launch",
    )
    assert egress_calls == [_CANDIDATE_POST_ID]
    assert seen_by_abac == [_CANDIDATE_POST_ID]


@pytest.mark.anyio
async def test_non_empty_global_ask_does_not_fall_back_to_unrelated_recent_posts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_semantic_candidates(
        _conn: Any,
        _question: str | None,
        *,
        maximum_candidates: int = 128,
    ) -> list[str]:
        assert maximum_candidates == 128
        return []

    monkeypatch.setattr(
        ingestion,
        "semantic_candidate_post_ids",
        no_semantic_candidates,
        raising=False,
    )
    connection = _FakeConnection(
        lexical_rows=[],
        final_rows=[_post_row(_UNRELATED_POST_ID, title="Newest unrelated post")],
    )

    sources = await ingestion.gather_global_chat_sources(
        connection,
        lambda _row: True,
        question="No persisted evidence matches this",
        limit=4,
    )

    assert sources == []
    assert connection.final_query_calls == 0
