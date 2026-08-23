"""Regression tests for reader-visible stale summary continuity."""

import asyncio
import hashlib
from types import SimpleNamespace
from typing import Self

import pytest

from backend.app import main
from backend.app.post_content_queue import FAILED, QUEUED, SUCCEEDED
from backend.app.post_summary_ingestion import fetch_persisted_summary
from lineageweave.post_summary import POST_SUMMARY_CONTRACT_VERSION


class _StaleSummaryConnection:
    """Minimal asyncpg-shaped fake containing one previous-contract summary."""

    async def fetchrow(self, query: str, post_id: str) -> dict[str, object]:
        return {
            "korean_summary": "Previously persisted evidence.",
            "summary_contract_version": 18,
        }

    async def fetch(self, query: str, post_id: str) -> list[dict[str, object]]:
        return []


class _BoundSummaryConnection(_StaleSummaryConnection):
    """One current-contract row with a configurable normalized-input binding."""

    def __init__(self, summary_input_sha256: str | None) -> None:
        self.summary_input_sha256 = summary_input_sha256

    async def fetchrow(self, query: str, post_id: str) -> dict[str, object]:
        assert "summary_input_sha256" in query
        return {
            "korean_summary": "Persisted synthetic evidence.",
            "summary_contract_version": POST_SUMMARY_CONTRACT_VERSION,
            "summary_input_sha256": self.summary_input_sha256,
        }


def test_stale_summary_is_hidden_by_default() -> None:
    """Current-contract reads must not silently present legacy semantics."""
    result = asyncio.run(fetch_persisted_summary(_StaleSummaryConnection(), "post-id"))
    assert result is None


def test_stale_summary_can_be_returned_with_explicit_status() -> None:
    """The continuity path exposes the old contract so the UI can label it."""
    result = asyncio.run(
        fetch_persisted_summary(_StaleSummaryConnection(), "post-id", allow_stale=True)
    )
    assert result is not None
    assert result["summary_status"] == "stale"
    assert result["summary_contract_version"] == 18
    assert result["korean_summary"] == "Previously persisted evidence."


def test_current_summary_requires_exact_normalized_input_binding() -> None:
    normalized_input = "Synthetic normalized evidence."
    digest = hashlib.sha256(normalized_input.encode("utf-8")).hexdigest()
    connection = _BoundSummaryConnection(digest)

    current = asyncio.run(
        fetch_persisted_summary(
            connection,
            "post-id",
            summary_input=normalized_input,
        )
    )
    mismatch = asyncio.run(
        fetch_persisted_summary(
            connection,
            "post-id",
            summary_input="Revised synthetic evidence.",
        )
    )
    revised_stale = asyncio.run(
        fetch_persisted_summary(
            connection,
            "post-id",
            summary_input="Revised synthetic evidence.",
            allow_stale=True,
        )
    )

    assert current is not None
    assert current["summary_status"] == "current"
    assert mismatch is None
    assert revised_stale is not None
    assert revised_stale["summary_status"] == "stale"


def test_legacy_unbound_summary_is_only_explicit_stale_continuity() -> None:
    connection = _BoundSummaryConnection(None)

    current = asyncio.run(
        fetch_persisted_summary(
            connection,
            "post-id",
            summary_input="Synthetic normalized evidence.",
        )
    )
    stale = asyncio.run(
        fetch_persisted_summary(
            connection,
            "post-id",
            summary_input="Synthetic normalized evidence.",
            allow_stale=True,
        )
    )

    assert current is None
    assert stale is not None
    assert stale["summary_status"] == "stale"


def test_reader_returns_stale_summary_without_waiting_for_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A popup read must not block on two slow provider calls when evidence exists."""

    class Connection:
        async def fetchrow(self, query: str, post_id: str) -> dict[str, object]:
            assert "select post_body" in query
            return {"post_body": "Synthetic release chronology."}

    class Acquire:
        async def __aenter__(self) -> Connection:
            return Connection()

        async def __aexit__(self, *_args: object) -> None:
            return None

    class Pool:
        def acquire(self) -> Acquire:
            return Acquire()

    async def load_visible_post(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"post_title": "Synthetic release chronology"}

    async def persisted_summary(
        _conn: object,
        _post_id: str,
        *,
        summary_input: str | None = None,
        allow_stale: bool = False,
    ) -> dict[str, object] | None:
        assert summary_input == "Synthetic release chronology."
        if not allow_stale:
            return None
        return {
            "summary_status": "stale",
            "summary_contract_version": 18,
            "korean_summary": "Previously persisted evidence.",
        }

    monkeypatch.setattr(main, "_load_visible_post", load_visible_post)
    monkeypatch.setattr(main, "build_post_llm_metadata", lambda *_args: {})
    monkeypatch.setattr(main, "fetch_persisted_summary", persisted_summary)
    monkeypatch.setattr(
        main,
        "_post_summary_client",
        lambda: (_ for _ in ()).throw(AssertionError("orchestrator must not be called")),
    )

    result = asyncio.run(
        main.read_post_summary(
            "00000000-0000-0000-0000-000000000001",
            account=object(),
            pool=Pool(),
            valkey=None,
        )
    )

    assert result["summary_status"] == "stale"
    assert result["summary_contract_version"] == 18


class _ImageSummaryConnection:
    """Asyncpg-shaped source-body connection for synthetic image-summary reads."""

    async def fetchrow(self, query: str, post_id: str) -> dict[str, object]:
        assert "select post_body" in query
        return {
            "post_body": "<p>Synthetic evidence.</p>"
            "<img src='data:image/png;base64,iVBORw0KGgo='>"
        }

    def transaction(self) -> "_ImageSummaryConnection":
        return self

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class _ImageSummaryPool:
    """Yield the same synthetic connection for one endpoint call."""

    def __init__(self) -> None:
        self.connection = _ImageSummaryConnection()

    def acquire(self) -> _ImageSummaryConnection:
        return self.connection


def _configure_image_summary_read(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ready: bool,
    job_status: str,
    current_summary: dict[str, object] | None,
    stale_summary: dict[str, object] | None = None,
    stored_summary_input: str | None = "Synthetic persisted image evidence.",
) -> list[str]:
    """Install a synthetic image-read boundary and return readiness calls."""
    readiness_calls: list[str] = []

    async def load_visible_post(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"post_title": "Synthetic image evidence"}

    async def persisted_summary(
        _conn: object,
        _post_id: str,
        *,
        summary_input: str | None = None,
        allow_stale: bool = False,
    ) -> dict[str, object] | None:
        if not ready:
            raise AssertionError("summary rows must not be read before current image readiness")
        if allow_stale:
            return stale_summary
        if summary_input != stored_summary_input:
            return None
        return current_summary

    async def content_complete(*_args: object, **_kwargs: object) -> bool:
        return ready

    async def ensure_job(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            status_code=job_status,
            should_publish=False,
            post_id="synthetic-post",
            source_body_sha256="a" * 64,
        )

    async def summary_ready(
        _conn: object,
        post_id: str,
        source_body_digest: str,
    ) -> bool:
        assert source_body_digest == "a" * 64
        readiness_calls.append(post_id)
        return ready

    async def summary_source(_conn: object, _post_id: str) -> str:
        return "Synthetic persisted image evidence."

    monkeypatch.setattr(main, "_load_visible_post", load_visible_post)
    monkeypatch.setattr(main, "build_post_llm_metadata", lambda *_args: {})
    monkeypatch.setattr(main, "fetch_persisted_summary", persisted_summary)
    monkeypatch.setattr(main, "post_body_has_images", lambda _body: True)
    monkeypatch.setattr(main, "post_content_is_complete", content_complete)
    monkeypatch.setattr(main, "ensure_post_content_job", ensure_job)
    monkeypatch.setattr(main, "post_content_summary_is_ready", summary_ready)
    monkeypatch.setattr(main, "fetch_post_summary_source", summary_source)
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: SimpleNamespace(
            embedding_model="",
            orchestrator_base_url="",
            orchestrator_api_key="",
        ),
    )
    monkeypatch.setattr(
        main,
        "_post_summary_client",
        lambda: (_ for _ in ()).throw(AssertionError("summary must not run")),
    )
    return readiness_calls


def test_pending_image_evidence_withholds_current_persisted_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A current contract cannot bypass incomplete persisted VISION evidence."""
    current = {"summary_status": "current", "korean_summary": "Synthetic summary."}
    calls = _configure_image_summary_read(
        monkeypatch,
        ready=False,
        job_status=QUEUED,
        current_summary=current,
    )

    with pytest.raises(main.HTTPException, match="still being processed"):
        asyncio.run(
            main.read_post_summary(
                "synthetic-post",
                account=object(),
                pool=_ImageSummaryPool(),
                valkey=None,
            )
        )

    assert calls == ["synthetic-post"]


def test_failed_image_evidence_reports_unavailable_instead_of_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A terminal image job cannot look active or expose a stored summary."""
    current = {"summary_status": "current", "korean_summary": "Synthetic summary."}
    calls = _configure_image_summary_read(
        monkeypatch,
        ready=False,
        job_status=FAILED,
        current_summary=current,
    )

    with pytest.raises(main.HTTPException, match="ingestion failed"):
        asyncio.run(
            main.read_post_summary(
                "synthetic-post",
                account=object(),
                pool=_ImageSummaryPool(),
                valkey=None,
            )
        )

    assert calls == ["synthetic-post"]


def test_ready_image_evidence_allows_current_persisted_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Readiness gates rather than discards a current persisted summary."""
    current = {"summary_status": "current", "korean_summary": "Synthetic summary."}
    calls = _configure_image_summary_read(
        monkeypatch,
        ready=True,
        job_status=SUCCEEDED,
        current_summary=current,
    )

    result = asyncio.run(
        main.read_post_summary(
            "synthetic-post",
            account=object(),
            pool=_ImageSummaryPool(),
            valkey=None,
        )
    )

    assert result == current
    assert calls == ["synthetic-post"]


def test_ready_image_evidence_does_not_return_unbound_stale_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale image summary must regenerate because it has no snapshot binding."""
    stale = {"summary_status": "stale", "korean_summary": "Old synthetic summary."}
    calls = _configure_image_summary_read(
        monkeypatch,
        ready=True,
        job_status=SUCCEEDED,
        current_summary=None,
        stale_summary=stale,
    )
    monkeypatch.setattr(
        main,
        "_post_summary_client",
        lambda: SimpleNamespace(available=False),
    )

    with pytest.raises(main.HTTPException, match="ORCHESTRATOR_BASE_URL"):
        asyncio.run(
            main.read_post_summary(
                "synthetic-post",
                account=object(),
                pool=_ImageSummaryPool(),
                valkey=None,
            )
        )

    assert calls == ["synthetic-post"]


def test_same_body_changed_image_evidence_regenerates_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changed persisted VISION text invalidates a same-body summary binding."""
    current = {"summary_status": "current", "korean_summary": "Old synthetic summary."}
    calls = _configure_image_summary_read(
        monkeypatch,
        ready=True,
        job_status=SUCCEEDED,
        current_summary=current,
        stored_summary_input="Earlier persisted image evidence.",
    )
    monkeypatch.setattr(
        main,
        "_post_summary_client",
        lambda: SimpleNamespace(available=False),
    )

    with pytest.raises(main.HTTPException, match="ORCHESTRATOR_BASE_URL"):
        asyncio.run(
            main.read_post_summary(
                "synthetic-post",
                account=object(),
                pool=_ImageSummaryPool(),
                valkey=None,
            )
        )

    assert calls == ["synthetic-post"]
