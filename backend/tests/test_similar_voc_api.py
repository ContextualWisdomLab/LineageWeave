"""Focused API contract tests for live Similar VOC evidence."""

from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from backend.app import main
from lineageweave.similar_voc import SimilarVocEvidence


class _Connection:
    def __init__(self, rows):
        self.rows = rows
        self.query = ""
        self.args = ()

    async def fetch(self, query, *args):
        self.query = query
        self.args = args
        return self.rows


class _Pool:
    def __init__(self, rows):
        self.connection = _Connection(rows)

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


def test_similar_voc_adjudicates_visible_semantic_candidates(monkeypatch) -> None:
    """The live endpoint omits an ABAC-hidden candidate and exposes no score."""
    focal = {
        "post_id": "focal",
        "post_title": "Current VOC",
        "post_body": "Current seal failed.",
    }
    visible = {
        "post_id": "prior",
        "post_title": "Prior VOC",
        "post_body": "Prior seal failed. Replaced gasket.",
        "visibility_code": "private",
        "corporate_entity_id": "corp-a",
        "process_unit_id": "process-a",
        "occurred_at": datetime(2026, 8, 20, tzinfo=timezone.utc),
    }
    hidden = {**visible, "post_id": "hidden", "visibility_code": "private", "corporate_entity_id": "corp-b"}

    async def load_visible_post(*_args):
        return focal

    class Client:
        def analyze(self, *_args):
            return SimilarVocEvidence(
                "prior", "Equivalent seal failure", "Current seal failed.",
                "Prior seal failed.", None, ("Replaced gasket.",),
            )

    monkeypatch.setattr(main, "_load_visible_post", load_visible_post)
    monkeypatch.setattr(main, "_similar_voc_client", Client)
    account = SimpleNamespace(
        corporate_entity_ids={"corp-a"}, process_unit_ids={"process-a"}
    )

    pool = _Pool([visible, hidden])
    payload = asyncio.run(main.read_similar_voc("focal", account, pool))

    assert [item["post_id"] for item in payload["items"]] == ["prior"]
    assert "score" not in payload["items"][0]
    assert payload["items"][0]["action_history"] == ("Replaced gasket.",)
    assert "process_unit_id::text = any($3::text[])" in pool.connection.query
    assert pool.connection.args == ("focal", ["corp-a"], ["process-a"])
