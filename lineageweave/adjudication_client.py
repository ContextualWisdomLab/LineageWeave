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

from .http_client import chat_completion_content, post_json


class AdjudicationClient(Protocol):
    """Judges one (candidate parent, record) pair; returns confidence in [0, 1]."""

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
        """Score the candidate and record labels for semantic adjudication."""
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
        content = chat_completion_content(body)
        match = _CONFIDENCE_PATTERN.search(content)
        if match is None:
            return 0.0
        return max(0.0, min(1.0, float(match.group(1))))
