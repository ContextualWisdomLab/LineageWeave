"""Reader content projections must be bound to the current durable job."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from backend.app import main
from backend.app.post_content_queue import (
    QUEUED,
    SUCCEEDED,
    PostContentJobRequest,
    source_body_sha256,
)

_POST_ID = "00000000-0000-0000-0000-000000000001"
_BODY = "A current synthetic source body."
_UNIT = {
    "unit_index": 0,
    "unit_kind_code": "dom",
    "unit_label": "p",
    "unit_text": "A current derived unit.",
    "indent_level": 0,
    "decision_source_code": "explicit",
    "structure_confidence": 1.0,
    "evidence_text": "Synthetic explicit structure.",
}


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args: object) -> bool:
        return False


class _Connection:
    def __init__(self, status_code: str, *, binding_body: str = _BODY) -> None:
        self.status_code = status_code
        self.binding_body = binding_body

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def fetchrow(self, query: str, *_args: object):
        if "join post_content_ingestion_job" in query:
            return {
                "post_body": self.binding_body,
                "source_body_sha256": source_body_sha256(_BODY),
                "status_code": self.status_code,
            }
        assert "select post_body from source_post" in query
        return {"post_body": _BODY}

    async def fetch(self, query: str, *_args: object):
        if "from post_content_unit unit" in query and "join post_content_image" not in query:
            return [_UNIT]
        if "join post_content_image image" in query:
            return []
        raise AssertionError("unexpected content query")


class _Pool:
    def __init__(self, status_code: str, *, binding_body: str = _BODY) -> None:
        self.status_code = status_code
        self.binding_body = binding_body

    @asynccontextmanager
    async def acquire(self):
        yield _Connection(self.status_code, binding_body=self.binding_body)


def _configure(
    monkeypatch: pytest.MonkeyPatch,
    *,
    status_code: str,
) -> None:
    async def visible(*_args, **_kwargs):
        return {}

    async def incomplete(*_args, **_kwargs) -> bool:
        return False

    async def ensure(*_args, **_kwargs) -> PostContentJobRequest:
        return PostContentJobRequest(
            _POST_ID,
            source_body_sha256(_BODY),
            status_code,
            False,
        )

    monkeypatch.setattr(main, "_load_visible_post", visible)
    monkeypatch.setattr(main, "post_content_is_complete", incomplete)
    monkeypatch.setattr(main, "ensure_post_content_job", ensure)
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: SimpleNamespace(
            embedding_model="",
            orchestrator_base_url="",
            orchestrator_api_key="",
        ),
    )


def test_processing_content_withholds_unbound_persisted_units(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch, status_code=QUEUED)

    payload = asyncio.run(
        main.read_post_content(
            _POST_ID,
            account=object(),
            pool=_Pool(QUEUED),
            valkey=None,
        )
    )

    assert payload["status"] == "processing"
    assert payload["units"] == []
    assert payload["images"] == []


def test_exact_current_succeeded_content_exposes_persisted_units(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch, status_code=SUCCEEDED)

    payload = asyncio.run(
        main.read_post_content(
            _POST_ID,
            account=object(),
            pool=_Pool(SUCCEEDED),
            valkey=None,
        )
    )

    assert payload["status"] == "ready"
    assert payload["units"][0]["unit_text"] == _UNIT["unit_text"]


def test_source_change_after_enqueue_withholds_succeeded_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch, status_code=SUCCEEDED)

    payload = asyncio.run(
        main.read_post_content(
            _POST_ID,
            account=object(),
            pool=_Pool(SUCCEEDED, binding_body="A newer synthetic source body."),
            valkey=None,
        )
    )

    assert payload["status"] == "processing"
    assert payload["units"] == []
    assert payload["images"] == []
