"""Derived Voice strict-schema and persistence regressions."""

from __future__ import annotations

import asyncio
import hashlib
import json

import pytest

from backend.app.voice_classification_ingestion import (
    persist_derived_voice_classification,
)
from lineageweave import voice_classification
from lineageweave.voice_classification import (
    ContextualOrchestratorVoiceClassificationClient,
    DerivedVoiceAssertion,
    VoiceClassificationResponseContractError,
    VoiceClassificationResult,
    parse_voice_classification_response,
)


def _response(
    assertions: list[dict[str, object]], *, receipt: object = "chatcmpl-synthetic"
) -> dict:
    return {
        "id": receipt,
        "choices": [{"message": {"content": json.dumps({"assertions": assertions})}}],
    }


def test_parser_accepts_receipt_bearing_multi_label_exact_spans() -> None:
    """Multiple governed concepts survive only with exact caller-owned offsets."""
    body = "A supplier note also records a process signal."
    result = parse_voice_classification_response(
        _response(
            [
                {
                    "voice_concept_code": "vos",
                    "evidence_span_start": 2,
                    "evidence_span_end": 15,
                    "evidence_text": "supplier note",
                },
                {
                    "voice_concept_code": "vops",
                    "evidence_span_start": 31,
                    "evidence_span_end": 45,
                    "evidence_text": "process signal",
                },
            ]
        ),
        body,
    )

    assert result.orchestrator_model_receipt == "chatcmpl-synthetic"
    assert [value.voice_concept_code for value in result.assertions] == ["vos", "vops"]
    assert result.source_revision_digest == hashlib.sha256(body.encode()).hexdigest()


@pytest.mark.parametrize(
    "response",
    [
        _response([], receipt=None),
        _response(
            [
                {
                    "voice_concept_code": "vos",
                    "evidence_span_start": 0,
                    "evidence_span_end": 8,
                    "evidence_text": "different",
                }
            ]
        ),
        _response(
            [
                {
                    "voice_concept_code": "vos",
                    "evidence_span_start": 0,
                    "evidence_span_end": 8,
                    "evidence_text": "supplier",
                },
                {
                    "voice_concept_code": "vos",
                    "evidence_span_start": 0,
                    "evidence_span_end": 8,
                    "evidence_text": "supplier",
                },
            ]
        ),
    ],
)
def test_parser_fails_closed_without_receipt_exact_span_or_unique_code(
    response: dict,
) -> None:
    """Invalid structured evidence is unavailable rather than repaired or guessed."""
    with pytest.raises(VoiceClassificationResponseContractError):
        parse_voice_classification_response(response, "supplier")


def test_client_uses_strict_schema_and_all_twelve_codes(monkeypatch) -> None:
    """The producer delegates semantic classification to strict orchestrator auto mode."""
    captured: dict = {}

    def post(_url, payload, **_kwargs):
        captured.update(payload)
        return _response([])

    monkeypatch.setattr(voice_classification, "post_json", post)
    result = ContextualOrchestratorVoiceClassificationClient(
        "https://gateway", "key"
    ).classify("Synthetic source with no supported Voice evidence.")

    schema = captured["response_format"]["json_schema"]
    assert captured["model"] == "orchestrator/auto"
    assert schema["strict"] is True
    assert (
        set(
            schema["schema"]["properties"]["assertions"]["items"]["properties"][
                "voice_concept_code"
            ]["enum"]
        )
        == voice_classification.VOICE_CONCEPT_CODES
    )
    assert result.assertions == ()


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class _Connection:
    def __init__(self, digest: str):
        self.digest = digest
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    def transaction(self):
        return _Transaction()

    async def fetchval(self, *_args):
        return self.digest

    async def fetch(self, *_args):
        return [
            {"classification_assertion_id": "prior-vos", "voice_concept_code": "vos"}
        ]

    async def execute(self, query: str, *args):
        self.executed.append((query, args))
        return "OK"


def test_persistence_closes_only_derived_history_and_records_successful_empty() -> None:
    """A valid empty result gets a receipt without fabricating a positive assertion."""
    digest = "a" * 64
    conn = _Connection(digest)
    asyncio.run(
        persist_derived_voice_classification(
            conn,
            "00000000-0000-0000-0000-000000000001",
            VoiceClassificationResult(digest, "chatcmpl-empty", ()),
        )
    )

    statements = [query for query, _args in conn.executed]
    assert any(
        "assertion_status_code = 'derived'" in query and "update" in query
        for query in statements
    )
    assert not any("values ($1::uuid, $2, 'derived'" in query for query in statements)
    assert any("post_voice_classification_analysis" in query for query in statements)


def test_persistence_links_same_code_successor_and_rejects_stale_revision() -> None:
    """A replacement names its prior same-code assertion; stale bodies fail closed."""
    digest = "b" * 64
    assertion = DerivedVoiceAssertion("vos", 0, 8, "c" * 64)
    conn = _Connection(digest)
    asyncio.run(
        persist_derived_voice_classification(
            conn,
            "00000000-0000-0000-0000-000000000001",
            VoiceClassificationResult(digest, "chatcmpl-next", (assertion,)),
        )
    )
    insert_args = next(
        args
        for query, args in conn.executed
        if "values ($1::uuid, $2, 'derived'" in query
    )
    assert insert_args[-1] == "prior-vos"

    with pytest.raises(ValueError, match="source revision"):
        asyncio.run(
            persist_derived_voice_classification(
                _Connection("d" * 64),
                "00000000-0000-0000-0000-000000000001",
                VoiceClassificationResult(digest, "chatcmpl-stale", ()),
            )
        )
