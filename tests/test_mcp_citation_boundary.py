"""Regression for the Global Ask citation trust boundary."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.app import global_ask
from backend.app.auth import CurrentAccount
from lineageweave.post_chat import ChatAnswer, ChatSourceDocument

_ACCOUNT = CurrentAccount(
    user_account_id="account-1",
    external_subject_id="subject-1",
    display_name="Analyst",
    corporate_entity_ids=frozenset(),
    permission_codes=frozenset({"post_read"}),
)
_ROW = {
    "post_id": "authorized-post",
    "post_title": "Authorized",
    "post_body": "evidence",
    "visibility_code": "public",
    "corporate_entity_id": None,
    "created_at": 1,
    "relevance_score": 3,
}


class _Connection:
    """Return one visible anchor for every bounded search term."""

    async def fetch(self, _sql: str, *_args: object):
        return [_ROW]


@dataclass
class _OutsideOnlyClient:
    """Return a citation that was never present in the authorized source bundle."""

    available: bool = True

    def answer(
        self,
        _question: str,
        _sources: list[ChatSourceDocument],
        *,
        session_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ChatAnswer:
        return ChatAnswer("unsupported answer", ("outside-source",))


@pytest.mark.asyncio
async def test_global_ask_rejects_an_answer_without_an_authorized_citation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An LLM answer cannot survive after all of its citations are filtered out."""

    async def gather(*_args, **_kwargs):
        return [ChatSourceDocument("authorized-post", "Authorized", "evidence")]

    monkeypatch.setattr(global_ask, "gather_chat_sources", gather)
    with pytest.raises(global_ask.GlobalAskUnavailableError, match="no citation"):
        await global_ask.answer_global_question(
            _Connection(),
            _ACCOUNT,
            _OutsideOnlyClient(),
            "authorized",
        )
