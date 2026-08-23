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

from .http_client import HttpClientError, post_json


class AdjudicationClient(Protocol):
    """Judges one (candidate parent, record) pair; returns confidence in [0, 1].

    Implementations must raise rather than return a placeholder score when a
    call fails (bad transport, malformed response, unparseable content):
    ``0.0`` is also a real "definitely unrelated" judgment, so a failure and
    a genuine negative verdict must stay distinguishable to every caller.
    """

    available: bool

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Score the candidate and record labels for semantic adjudication."""
        raise NotImplementedError


class NullAdjudicationClient:
    """No LLM orchestrator configured -- the llm channel is skipped."""

    available = False

    def judge(self, candidate_label: str, record_label: str) -> float:  # pragma: no cover
        """Score the candidate and record labels for semantic adjudication."""
        raise RuntimeError("NullAdjudicationClient has no llm channel; check .available first")


_CONFIDENCE_PATTERN = re.compile(r"([01](?:\.\d+)?)")


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
        """Score the candidate and record labels for semantic adjudication.

        Raises:
            HttpClientError: the gateway responded but its content could not
                be parsed into a confidence score (missing/malformed message
                shape, or no ``[01](\\.\\d+)?`` number in the reply). This is
                a channel failure, not a real judgment -- ``0.0`` is also a
                legitimate "definitely unrelated" score, so a parse failure
                must never be conflated with one by returning it silently
                (see module docstring and ``NullAdjudicationClient``).
        """
        prompt = (
            "On a scale from 0.0 (definitely unrelated) to 1.0 (definitely the same "
            "thread, B directly follows from A), how confident are you that record B "
            "is a direct continuation of record A? Reply with only the number.\n\n"
            f"Record A: {candidate_label}\nRecord B: {record_label}"
        )
        body = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "messages": [{"role": "user", "content": prompt}],
                "mode": "auto",
                "reasoning_effort": self._reasoning_effort,
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HttpClientError(
                "adjudication response is missing choices[0].message.content"
            ) from exc
        if not isinstance(content, str):
            raise HttpClientError(
                f"adjudication response content was not a string: {content!r}"
            )
        match = _CONFIDENCE_PATTERN.search(content)
        if match is None:
            raise HttpClientError(
                f"adjudication response had no parseable confidence score: {content!r}"
            )
        return max(0.0, min(1.0, float(match.group(1))))
