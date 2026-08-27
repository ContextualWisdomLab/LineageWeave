"""Pluggable LLM-adjudication channel: does ``child`` plausibly follow from
``candidate``?

The default :class:`NullAdjudicationClient` makes the channel unavailable.
:class:`ContextualOrchestratorAdjudicationClient` calls a running
`contextual-orchestrator <https://github.com/ContextualWisdomLab/contextual-orchestrator>`_
instance's ``mode="auto"`` completion. The orchestrator selects the supported
route and records its verification metadata
so this channel gets a reasoned, checked verdict rather than a bare
similarity score, without paying for a full multi-step workflow per pair.
"""

from __future__ import annotations

import re
from typing import Protocol

from .http_client import HttpClientError, chat_completion_content, post_json


class AdjudicationClient(Protocol):
    """Judges one (candidate parent, record) pair; returns confidence in [0, 1]."""

    available: bool

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Score the candidate and record labels for semantic adjudication."""
        raise NotImplementedError


class AdjudicationClientError(RuntimeError):
    """The provider returned an unusable adjudication response."""


class NullAdjudicationClient:
    """No LLM orchestrator configured -- the llm channel is skipped."""

    available = False

    def judge(self, candidate_label: str, record_label: str) -> float:  # pragma: no cover
        """Score the candidate and record labels for semantic adjudication."""
        raise RuntimeError("NullAdjudicationClient has no llm channel; check .available first")


_CONFIDENCE_PATTERN = re.compile(r"([01](?:\.\d+)?)")
_STRICT_CONFIDENCE_PATTERN = re.compile(r"(?:0(?:\.\d+)?|1(?:\.0+)?)")


def parse_confidence_response(content: object) -> float:
    """Parse the provider's number-only confidence response strictly."""

    if not isinstance(content, str):
        raise AdjudicationClientError("provider confidence response was not text")
    normalized = content.strip()
    if _STRICT_CONFIDENCE_PATTERN.fullmatch(normalized) is None:
        raise AdjudicationClientError(
            "provider confidence response was not a number in 0..1"
        )
    return float(normalized)


def judge_prompt(candidate_label: str, record_label: str) -> str:
    """The one adjudication prompt, shared by the live client and the
    queued batch scorer so both channels ask the identical question."""
    return (
        "On a scale from 0.0 (definitely unrelated) to 1.0 (definitely the same "
        "thread, B directly follows from A), how confident are you that record B "
        "is a direct continuation of record A? Reply with only the number.\n\n"
        f"Record A: {candidate_label}\nRecord B: {record_label}"
    )


def parse_confidence(content: str) -> float:
    """Clamp a numeric reply into ``[0, 1]`` or fail without inventing zero."""
    parsed = parse_confidence_or_none(content)
    if parsed is None:
        raise HttpClientError("adjudication response had no confidence score")
    return parsed


def parse_confidence_or_none(content: str) -> float | None:
    """Like :func:`parse_confidence`, but an unparseable reply is ``None``.

    The queued batch scorer must distinguish "the judge said 0.0" from
    "the judge failed to answer" -- persisting the latter as a confident
    zero would fabricate an unrelated verdict for an errored request.
    """
    match = _CONFIDENCE_PATTERN.search(content)
    if match is None:
        return None
    return max(0.0, min(1.0, float(match.group(1))))


class ContextualOrchestratorAdjudicationClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="auto"``.

    Reasoning effort defaults to ``"auto"`` so contextual-orchestrator owns
    test-time-compute allocation; callers may still request an explicit level.
    """

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "auto", timeout: float = 180.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Score the candidate and record labels for semantic adjudication."""
        body = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "messages": [
                    {"role": "user", "content": judge_prompt(candidate_label, record_label)}
                ],
                "mode": "auto",
                "reasoning_effort": self._reasoning_effort,
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        try:
            content = chat_completion_content(body)
        except (TypeError, ValueError) as exc:
            raise AdjudicationClientError(
                "provider response did not contain one chat message"
            ) from exc
        return parse_confidence_response(content)
