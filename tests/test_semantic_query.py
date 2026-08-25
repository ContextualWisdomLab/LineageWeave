"""Tests for evidence-constrained semantic query rewriting."""

import pytest

from lineageweave.semantic_query import (
    ContextualOrchestratorSemanticQueryClient,
    NullSemanticQueryClient,
)


def test_rewriter_keeps_literal_multilingual_phrases(monkeypatch) -> None:
    """A rewrite may remove framing but cannot invent or translate a concept."""

    monkeypatch.setattr(
        "lineageweave.semantic_query.post_json",
        lambda *_args, **_kwargs: {
            "choices": [
                {"message": {"content": '{"search_phrases":["Apollo", "책임자", "Apollo"]}'}}
            ]
        },
    )
    client = ContextualOrchestratorSemanticQueryClient("https://orchestrator.test", "secret")

    assert client.rewrite("Apollo 프로젝트의 책임자는 누구입니까?") == ("Apollo", "책임자")


@pytest.mark.parametrize(
    "content",
    [
        '{"search_phrases":["Phoenix"]}',
        '{"search_phrases":[]}',
        '{"search_phrases":[1]}',
        '{"search_phrases":["APOLLO"]}',
        "[]",
    ],
)
def test_rewriter_rejects_invented_or_malformed_phrases(monkeypatch, content: str) -> None:
    """Provider output cannot introduce a term absent from the question."""

    monkeypatch.setattr(
        "lineageweave.semantic_query.post_json",
        lambda *_args, **_kwargs: {"choices": [{"message": {"content": content}}]},
    )
    client = ContextualOrchestratorSemanticQueryClient("https://orchestrator.test", "secret")

    with pytest.raises(ValueError):
        client.rewrite("What is known about Apollo?")


def test_null_rewriter_is_explicitly_unavailable() -> None:
    """Missing orchestration never fabricates a rewrite."""

    client = NullSemanticQueryClient()

    assert client.available is False
    with pytest.raises(RuntimeError):
        client.rewrite("Apollo")
