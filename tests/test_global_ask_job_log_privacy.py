"""ADR 0122 job diagnostics never serialize job IDs, values, or causes."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from backend.app import global_ask_queue as queue


class _Connection:
    def __init__(self, present=True):
        self.present = present
        self.executed = []
        self.claims = 0
        self.generation = object()

    async def fetchrow(self, *_args):
        self.claims += 1
        if not self.present:
            return None
        return {
            "requesting_account_id": "synthetic-requester",
            "question_text": "Synthetic question",
            "verify_external_requested": False,
            "knowledge_cutoff": None,
            "updated_at": self.generation,
        }

    async def execute(self, query, *args):
        self.executed.append((query, args))
        return "UPDATE 1"


class _Pool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _bind(monkeypatch, *, error=None, phase="compute", present=True):
    conn = _Connection(present)
    calls = []
    payload = {"answer_text": "Synthetic answer", "cited_post_ids": []}

    async def visibility(*_args):
        calls.append("visibility")
        if phase == "visibility" and error is not None:
            raise error
        return {"synthetic-corp"}, set(), False, True

    async def compute(*_args, **_kwargs):
        calls.append("compute")
        if phase == "compute" and error is not None:
            raise error
        return payload

    monkeypatch.setattr(queue, "load_job_visibility", visibility)
    monkeypatch.setattr(queue, "compute_global_ask_answer", compute)
    return conn, calls, payload


@pytest.mark.parametrize("phase", ["visibility", "compute"])
@pytest.mark.parametrize("kind", ["transport", "unexpected", "long", "safe", "timeout"])
def test_job_failure_log_is_type_only_and_preserves_settlement(monkeypatch, caplog, phase, kind):
    """Observe actual formatting while preserving every existing detail branch."""
    value = "synthetic-private-job-value"
    cause = "synthetic-private-job-cause"
    types = {
        "transport": ConnectionResetError,
        "unexpected": RuntimeError,
        "long": type("Synthetic" + "Long" * 40, (RuntimeError,), {}),
        "safe": queue._SafeJobError,
        "timeout": asyncio.TimeoutError,
    }
    error = types[kind](value)
    error.__cause__ = ValueError(cause)
    conn, calls, _ = _bind(monkeypatch, error=error, phase=phase)
    job_id = "synthetic-private-job-identifier"
    caplog.set_level(logging.ERROR, logger=queue.__name__)
    asyncio.run(queue.process_global_ask_job(
        _Pool(conn), job_id=job_id,
        chat_factory=lambda: SimpleNamespace(available=True),
    ))
    assert conn.claims == 1
    assert calls == ["visibility"] + (["compute"] if phase == "compute" else [])
    assert len(conn.executed) == 1
    sql, args = conn.executed[0]
    assert "failure_detail = $3" in sql
    detail = (value if kind == "safe" else
              "Ask Agent is unavailable: contextual-orchestrator returned no complete evidence object")
    assert args == (job_id, queue.FAILED, detail, queue.RUNNING, conn.generation)
    assert "job_status_code = $4" in sql and "updated_at = $5" in sql
    records = [r for r in caplog.records if r.name == queue.__name__]
    assert len(records) == 1 and records[0].levelno == logging.ERROR
    assert value not in caplog.text and cause not in caplog.text and job_id not in caplog.text
    assert records[0].exc_info is None and records[0].stack_info is None
    assert records[0].getMessage() == (
        "global ask job failed (error_type=%s)" % type(error).__name__[:128]
    )


@pytest.mark.parametrize("phase", ["visibility", "compute"])
def test_job_cancellation_is_silent_same_object_and_unsettled(monkeypatch, caplog, phase):
    """Shutdown preserves the claimed row for recovery without another write."""
    error = asyncio.CancelledError()
    conn, calls, _ = _bind(monkeypatch, error=error, phase=phase)
    caplog.set_level(logging.DEBUG, logger=queue.__name__)
    with pytest.raises(asyncio.CancelledError) as caught:
        asyncio.run(queue.process_global_ask_job(
            _Pool(conn), job_id="synthetic-job",
            chat_factory=lambda: SimpleNamespace(available=True),
        ))
    assert caught.value is error
    assert calls == ["visibility"] + (["compute"] if phase == "compute" else [])
    assert conn.claims == 1 and conn.executed == []
    assert not [r for r in caplog.records if r.name == queue.__name__]


@pytest.mark.parametrize("present", [False, True], ids=["duplicate-no-claim", "success"])
def test_job_nonfailure_controls_are_silent(monkeypatch, caplog, present):
    """A duplicate does no work; a successful claim stores the exact payload."""
    conn, calls, payload = _bind(monkeypatch, present=present)
    caplog.set_level(logging.DEBUG, logger=queue.__name__)
    asyncio.run(queue.process_global_ask_job(
        _Pool(conn), job_id="synthetic-job",
        chat_factory=lambda: SimpleNamespace(available=True),
    ))
    assert conn.claims == 1
    if present:
        assert calls == ["visibility", "compute"] and len(conn.executed) == 1
        sql, args = conn.executed[0]
        assert "answer_payload = $3::jsonb" in sql
        assert args == ("synthetic-job", queue.SUCCEEDED, queue._to_json(payload),
                        queue.RUNNING, conn.generation)
        assert "job_status_code = $4" in sql and "updated_at = $5" in sql
    else:
        assert calls == [] and conn.executed == []
    assert not [r for r in caplog.records if r.name == queue.__name__]
