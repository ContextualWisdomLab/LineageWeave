"""Consume TEPP time / multilevel / topic / KG from clues on the opened post.

Project, customer, org, and time window come from the post and 고객
마스터. Buyer chrome does not start an analysis-run and does not
persist a TEPP receipt. This Cloud slice fail-closes after clues
are checked. Never invents a theta.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .tepp_client import TeppClient

PROJECT_EMPTY_NEXT_ACTION = "이 글의 프로젝트를 아직 받을 수 없습니다"
CUSTOMER_EMPTY_NEXT_ACTION = "이 글의 고객을 아직 받을 수 없습니다"
ORG_EMPTY_NEXT_ACTION = "이 글의 조직을 아직 받을 수 없습니다"
TIME_WINDOW_EMPTY_NEXT_ACTION = "이 글의 시간창을 아직 받을 수 없습니다"
TEPP_UNAVAILABLE_NEXT_ACTION = "이 글의 시간·다층·토픽을 아직 받을 수 없습니다"

_TRAILING_PUNCT = re.compile(r"[?.!\s]+$")
_TEPP_QUESTION_TOKENS = (
    "시간창",
    "시간",
    "다층",
    "토픽",
    "지식그래프",
    "kg",
    "multilevel",
    "topic",
    "time window",
)


@dataclass(frozen=True)
class TeppClues:
    """Clues read from the opened post / 고객 마스터. Never invented."""

    project_id: str | None
    customer_id: str | None
    customer_name: str | None
    org_id: str | None
    org_name: str | None
    time_window: str | None


@dataclass(frozen=True)
class TeppConsumeResult:
    """Fail-closed consume. Not a completed measurement and not a receipt."""

    consumed: bool
    empty_next_action: str | None


def clues_from_opened_post(
    *,
    project_id: str | None,
    customer_id: str | None,
    customer_name: str | None,
    org_id: str | None,
    org_name: str | None,
    created_at: datetime | str | None,
) -> TeppClues:
    """Copy clues from authorized post fields. Empty stays empty."""
    clock: str | None = None
    if isinstance(created_at, datetime):
        clock = created_at.date().isoformat()
    elif created_at is not None:
        text = str(created_at).strip()
        clock = text[:10] if text else None
    return TeppClues(
        project_id=_optional_text(project_id),
        customer_id=_optional_text(customer_id),
        customer_name=_optional_text(customer_name),
        org_id=_optional_text(org_id),
        org_name=_optional_text(org_name),
        time_window=clock,
    )


def missing_clue_next_action(clues: TeppClues) -> str | None:
    """Name the next human action for the first missing required clue."""
    if not clues.time_window:
        return TIME_WINDOW_EMPTY_NEXT_ACTION
    if not clues.customer_id and not clues.customer_name:
        return CUSTOMER_EMPTY_NEXT_ACTION
    if not clues.org_id and not clues.org_name:
        return ORG_EMPTY_NEXT_ACTION
    if not clues.project_id:
        return PROJECT_EMPTY_NEXT_ACTION
    return None


def needs_tepp_consume(question: str) -> bool:
    """True when the question asks for TEPP time / multilevel / topic / KG."""
    folded = _TRAILING_PUNCT.sub("", " ".join(question.strip().lower().split()))
    return any(token in folded for token in _TEPP_QUESTION_TOKENS)


def consume_tepp_for_clues(client: TeppClient, clues: TeppClues) -> TeppConsumeResult:
    """Fail-close after reading clues. Do not start a TEPP run from buyer chrome.

    ``client`` is accepted so the existing versioned transport stays the
    consume surface, but this Cloud slice never submits and never
    invents a theta or a receipt.
    """
    del client
    missing = missing_clue_next_action(clues)
    if missing is not None:
        return TeppConsumeResult(consumed=False, empty_next_action=missing)
    return TeppConsumeResult(consumed=False, empty_next_action=TEPP_UNAVAILABLE_NEXT_ACTION)


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


__all__ = [
    "CUSTOMER_EMPTY_NEXT_ACTION",
    "ORG_EMPTY_NEXT_ACTION",
    "PROJECT_EMPTY_NEXT_ACTION",
    "TEPP_UNAVAILABLE_NEXT_ACTION",
    "TIME_WINDOW_EMPTY_NEXT_ACTION",
    "TeppClues",
    "TeppConsumeResult",
    "clues_from_opened_post",
    "consume_tepp_for_clues",
    "missing_clue_next_action",
    "needs_tepp_consume",
]
