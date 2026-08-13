"""Pluggable LLM-adjudication channel: does ``child`` plausibly follow from
``candidate``?

The default :class:`NullAdjudicationClient` makes the channel unavailable.
:class:`ContextualOrchestratorAdjudicationClient` calls a running
`contextual-orchestrator <https://github.com/ContextualWisdomLab/contextual-orchestrator>`_
instance's ``mode="verify"`` completion (one worker call plus one checked
verifier judgment -- see that repo's ``TaskOrchestrator.route_and_verify``)
so this channel gets a reasoned, checked verdict rather than a bare
similarity score, without paying for a full multi-step workflow per pair.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.request
from typing import Protocol

import certifi

# See lineageweave.embedding_client for why this is needed: some
# interpreter distributions don't reliably inherit the OS trust store, so
# point explicitly at certifi's maintained CA bundle (full validation still
# applies -- nothing here is weakened).
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class AdjudicationClient(Protocol):
    """Judges one (candidate parent, record) pair; returns confidence in [0, 1]."""

    available: bool

    def judge(self, candidate_label: str, record_label: str) -> float: ...


class NullAdjudicationClient:
    """No LLM orchestrator configured -- the llm channel is skipped."""

    available = False

    def judge(self, candidate_label: str, record_label: str) -> float:  # pragma: no cover
        raise RuntimeError("NullAdjudicationClient has no llm channel; check .available first")


_CONFIDENCE_PATTERN = re.compile(r"([01](?:\.\d+)?)")


class ContextualOrchestratorAdjudicationClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="verify"``.

    Reasoning effort defaults to ``"high"`` -- an adjudication call is
    exactly the low-volume, judgment-heavy case Fugu/Conductor/TRINITY-style
    test-time-compute allocation argues for spending more effort on
    (contextual-orchestrator's ``reasoning_effort`` request field).
    """

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "high", timeout: float = 60.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def judge(self, candidate_label: str, record_label: str) -> float:
        prompt = (
            "On a scale from 0.0 (definitely unrelated) to 1.0 (definitely the same "
            "thread, B directly follows from A), how confident are you that record B "
            "is a direct continuation of record A? Reply with only the number.\n\n"
            f"Record A: {candidate_label}\nRecord B: {record_label}"
        )
        payload = json.dumps(
            {
                "messages": [{"role": "user", "content": prompt}],
                "mode": "verify",
                "reasoning_effort": self._reasoning_effort,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/v1/chat/completions",
            data=payload,
            headers={"authorization": f"Bearer {self._api_key}", "content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout, context=_SSL_CONTEXT) as response:  # nosec B310 -- base_url is operator-configured, not request-controlled.
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        match = _CONFIDENCE_PATTERN.search(content)
        if match is None:
            return 0.0
        return max(0.0, min(1.0, float(match.group(1))))
