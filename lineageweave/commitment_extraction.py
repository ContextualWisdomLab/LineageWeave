"""Pluggable LLM derivation of a customer commitment from a post's text --
the "고객과의 약속에 관해서 LLM 자동 도출" and "이슈 관리는 To Do 와
캘린더로 자동 등록" product-brief items, unified: a derived commitment
*is* the ticket that gets registered as a to-do/calendar entry
(``issue_ticket.due_date`` + ``commitment_summary``; see
``GET /api/calendar``).

A commitment is a promise with a deadline ("we'll send the revised quote
by Friday"), not a general key event (Doddington et al., 2004's ACE-style
event extraction, already used by ``post_summary.py``) -- it specifically
needs a resolved due date, which is why the prompt is given a reference
date and asked to resolve relative phrases ("by next Friday", "within two
weeks") against it, per the same relative-time-resolution problem general
temporal-expression-normalization work addresses (Chambers & Jurafsky,
2008, TimeML/TempEval-style resolution). Not every post has a commitment
at all -- ``has_commitment: False`` is a legitimate, meaningful negative
result, not a parse failure, so it stays distinguishable from "the LLM's
response was malformed" the same way every other parser in this repo
keeps missing-vs-empty distinguishable.

Same pluggable-client, never-fake-a-missing-channel discipline as every
other channel: :class:`NullCommitmentExtractionClient` makes the channel
unavailable, never invents a commitment.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from .http_client import post_json


@dataclass(frozen=True)
class CustomerCommitment:
    """One post's derived commitment, or the explicit absence of one."""

    has_commitment: bool
    commitment_summary: str | None = None
    due_date: str | None = None  # ISO 8601 date (YYYY-MM-DD)


class CommitmentExtractionClient(Protocol):
    """Derives a customer commitment (if any) from a post's text."""

    available: bool

    def extract(self, post_title: str, post_body: str, reference_date: str) -> CustomerCommitment:
        """Return the post's derived commitment, resolving relative dates
        against ``reference_date`` (an ISO 8601 date).

        Implementations must raise if they cannot run extraction at all
        (e.g. the provider is unreachable). Protocol stubs raise
        ``NotImplementedError`` so a no-op body is never treated as a
        successful "no commitment" result.
        """
        raise NotImplementedError


class NullCommitmentExtractionClient:
    """No LLM orchestrator configured -- commitment derivation is unavailable."""

    available = False

    def extract(self, post_title: str, post_body: str, reference_date: str) -> CustomerCommitment:
        raise RuntimeError("NullCommitmentExtractionClient cannot extract; check .available first")


_COMMITMENT_PROMPT_TEMPLATE = """\
Read the post below (it may be in English, Korean, or mixed) and decide
whether it contains a genuine commitment or promise made to or with a
customer -- something with an explicit or clearly implied deadline (e.g.
"we will send the revised quote by Friday", "confirm the inspection
window within two weeks"). A general status update, opinion, or event
with no deadline is NOT a commitment.

Today's date, for resolving any relative date phrases ("by Friday",
"within two weeks", "next month"), is {reference_date}.

Reply with ONLY a JSON object (no markdown fences, no prose) with exactly
these fields:
  "has_commitment": boolean
  "commitment_summary": string or null -- a short, genuinely re-worded
    description of the commitment (required if has_commitment is true,
    null otherwise)
  "due_date": string or null -- the resolved absolute date in YYYY-MM-DD
    format (required if has_commitment is true and a date is stated or
    clearly implied, null otherwise)

Post title: {title}
Post body: {body}
"""

_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _strip_code_fence(content: str) -> str:
    match = _CODE_FENCE_PATTERN.search(content)
    return match.group(1) if match else content


def parse_commitment_response(content: str) -> CustomerCommitment | None:
    """Parses the LLM's JSON object response into a `CustomerCommitment`.

    Returns `None` (a parse failure) if the response is not a well-formed
    object with a boolean `has_commitment`. Returns
    `CustomerCommitment(has_commitment=False)` -- not `None` -- when the
    LLM legitimately found no commitment; that is a real, meaningful
    result, not a failure to parse.
    """
    try:
        parsed = json.loads(_strip_code_fence(content).strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None

    has_commitment = parsed.get("has_commitment")
    if not isinstance(has_commitment, bool):
        return None
    if not has_commitment:
        return CustomerCommitment(has_commitment=False)

    summary = parsed.get("commitment_summary")
    if not isinstance(summary, str) or not summary.strip():
        return None

    due_date = parsed.get("due_date")
    if due_date is not None and not (isinstance(due_date, str) and _ISO_DATE_PATTERN.match(due_date)):
        due_date = None

    return CustomerCommitment(has_commitment=True, commitment_summary=summary.strip(), due_date=due_date)


class ContextualOrchestratorCommitmentExtractionClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="auto"``."""

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "medium", timeout: float = 60.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def extract(self, post_title: str, post_body: str, reference_date: str) -> CustomerCommitment:
        prompt = _COMMITMENT_PROMPT_TEMPLATE.format(
            reference_date=reference_date, title=post_title, body=post_body
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
        content = body["choices"][0]["message"]["content"]
        commitment = parse_commitment_response(content)
        if commitment is None:
            raise ValueError(f"commitment response did not match the required format: {content!r}")
        return commitment
