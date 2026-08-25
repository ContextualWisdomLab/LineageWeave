"""Evidence-honest Global Ask knowledge-cutoff contracts."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from backend.app.post_chat_ingestion import gather_global_chat_sources
from lineageweave.post_chat import (
    ChatSourceDocument,
    ask_grounding_status,
    cited_post_summaries,
    historical_body_limitations,
)


_POST_ID = "11111111-1111-1111-1111-111111111111"
_REVISION_ID = "22222222-2222-2222-2222-222222222222"
_CUTOFF = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)


class _CutoffConnection:
    """Serve one candidate, one live row, and an optional retained revision."""

    def __init__(self, *, retain_revision: bool = True) -> None:
        self.retain_revision = retain_revision
        self.queries: list[str] = []

    async def fetch(self, query: str, *args):
        self.queries.append(query)
        if "with evidence_query" in query and "source_post_revision revision" in query:
            assert args[1] == _CUTOFF
            return [{"candidate_channel": "evidence", "post_id": _POST_ID}]
        if "select distinct on (post_id)" in query:
            if not self.retain_revision:
                return []
            return [
                {
                    "post_id": _POST_ID,
                    "source_post_revision_id": _REVISION_ID,
                    "post_title": "Apollo at cutoff",
                    "post_body": "Retained Apollo evidence.",
                    "written_at": datetime(2026, 1, 10, tzinfo=timezone.utc),
                }
            ]
        if "from post_project_mention" in query and "union all" in query:
            assert args[1] == _CUTOFF
            return []
        if "from source_post" in query:
            assert args[-1] == _CUTOFF
            return [
                {
                    "post_id": _POST_ID,
                    "post_title": "Apollo live rewrite",
                    "post_body": "Future rewrite must not enter the answer.",
                    "visibility_code": "public",
                    "corporate_entity_id": None,
                    "process_unit_id": None,
                    "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "updated_at": datetime(2026, 1, 20, tzinfo=timezone.utc),
                    "event_occurred_at": None,
                }
            ]
        raise AssertionError(query)


def test_cutoff_sources_use_retained_revision_and_exclude_current_only_channels() -> None:
    """The LLM sees the retained body, never the later live rewrite."""

    connection = _CutoffConnection()
    sources = asyncio.run(
        gather_global_chat_sources(
            connection,
            lambda _row: True,
            question="Apollo",
            knowledge_cutoff=_CUTOFF,
        )
    )

    assert len(sources) == 1
    source = sources[0]
    assert source.post_title == "Apollo at cutoff"
    assert source.post_body == "Retained Apollo evidence."
    assert source.source_post_revision_id == _REVISION_ID
    assert source.live_changed_after_cutoff is True
    assert source.historical_body_unavailable is False
    assert source.unavailable_channels == (
        "semantic_role",
        "semantic_keyman",
        "knowledge_graph",
        "lineage",
        "image",
    )
    assert any("post.created_at <= $2" in query for query in connection.queries)
    assert all("post_content_embedding" not in query for query in connection.queries)


def test_missing_cutoff_revision_is_an_explicit_limitation_not_live_fallback() -> None:
    """A missing retained body stays unavailable and exposes no live text."""

    sources = asyncio.run(
        gather_global_chat_sources(
            _CutoffConnection(retain_revision=False),
            lambda _row: True,
            question="Apollo",
            knowledge_cutoff=_CUTOFF,
        )
    )

    assert sources[0].post_title == "Historical body unavailable"
    assert sources[0].post_body == ""
    assert sources[0].historical_body_unavailable is True
    assert historical_body_limitations(sources) == [
        {
            "post_id": _POST_ID,
            "limitation_code": "historical_body_unavailable",
            "unavailable_channels": list(sources[0].unavailable_channels),
        }
    ]
    assert ask_grounding_status(sources, _CUTOFF.isoformat()) == "partially_cutoff_grounded"


def test_cutoff_citation_identifies_revision_clock_and_limitations() -> None:
    """Citation provenance is revision-specific while live citations stay compatible."""

    cutoff_source = ChatSourceDocument(
        _POST_ID,
        "Apollo at cutoff",
        "Retained body",
        source_post_revision_id=_REVISION_ID,
        evidence_available_at="2026-01-10T00:00:00+00:00",
        knowledge_cutoff=_CUTOFF.isoformat(),
        live_changed_after_cutoff=True,
        unavailable_channels=("knowledge_graph",),
    )
    live_source = ChatSourceDocument("live-post", "Live", "Live body")

    cutoff = cited_post_summaries([cutoff_source], [_POST_ID])[0]
    live = cited_post_summaries([live_source], ["live-post"])[0]

    assert cutoff["source_post_revision_id"] == _REVISION_ID
    assert cutoff["knowledge_cutoff"] == _CUTOFF.isoformat()
    assert cutoff["live_changed_after_cutoff"] is True
    assert live == {"post_id": "live-post", "post_title": "Live"}
    assert ask_grounding_status([cutoff_source], _CUTOFF.isoformat()) == "fully_cutoff_grounded"
