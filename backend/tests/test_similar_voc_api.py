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

    async def fetch(self, *_args):
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
        "visibility_code": "public",
        "corporate_entity_id": "corp-a",
        "process_unit_id": "unit-a",
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
    account = SimpleNamespace(corporate_entity_ids={"corp-a"}, process_unit_ids={"unit-a"})

    payload = asyncio.run(main.read_similar_voc("focal", 0, account, _Pool([visible, hidden])))

    assert [item["post_id"] for item in payload["items"]] == ["prior"]
    assert "score" not in payload["items"][0]
    assert payload["items"][0]["action_history"] == ("Replaced gasket.",)
    assert payload["next_offset"] is None


def test_similar_voc_pages_orchestrator_work(monkeypatch) -> None:
    """One request adjudicates only one bounded page and exposes continuation."""
    focal = {"post_id": "focal", "post_title": "Current", "post_body": "Current issue."}

    async def load_visible_post(*_args):
        return focal

    calls: list[str] = []

    class Client:
        def analyze(self, _title, _body, candidate_id, _candidate_title, candidate_body):
            calls.append(candidate_id)
            return SimilarVocEvidence(
                candidate_id, "Equivalent issue", "Current issue.", candidate_body,
                None, (),
            )

    rows = [
        {
            "post_id": f"prior-{index}",
            "post_title": f"Prior {index}",
            "post_body": f"Prior issue {index}.",
            "visibility_code": "public",
            "corporate_entity_id": "corp-a",
            "process_unit_id": "unit-a",
            "occurred_at": datetime(2026, 8, 20, tzinfo=timezone.utc),
        }
        for index in range(9)
    ]
    monkeypatch.setattr(main, "_load_visible_post", load_visible_post)
    monkeypatch.setattr(main, "_similar_voc_client", Client)
    account = SimpleNamespace(corporate_entity_ids={"corp-a"}, process_unit_ids={"unit-a"})

    payload = asyncio.run(main.read_similar_voc("focal", 16, account, _Pool(rows)))

    assert len(calls) == 8
    assert payload["next_offset"] == 24
