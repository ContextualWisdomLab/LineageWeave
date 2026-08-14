"""Pluggable Keyman extraction: which people does a post mention, are they
"our side" or a counterparty, and which organizations are they affiliated
with (a person may have N affiliations -- an internal Keyman can span
multiple group companies, a counterparty Keyman can span multiple external
orgs, per the product requirement).

The default :class:`NullKeymanExtractionClient` makes the channel
unavailable, same never-fake-a-missing-signal discipline as
``embedding_client``/``adjudication_client``/``image_content``.
:class:`ContextualOrchestratorKeymanExtractionClient` calls a running
contextual-orchestrator instance -- never a raw LLM API directly, per
AGENTS.md -- because Keyman identification is a structured-extraction task
that benefits from the orchestrator's reasoning-effort allocation, not a
single confidence number, so it uses ``mode="route"`` (one worker call) at
a ``"medium"`` reasoning effort by default rather than ``verify``'s
worker-plus-checker pattern, which is reserved for adjudication's binary
judgment calls.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Protocol

from .http_client import post_json

OUR_SIDE = "our_side"
COUNTERPARTY = "counterparty"
_VALID_SIDES = frozenset({OUR_SIDE, COUNTERPARTY})


@dataclass(frozen=True)
class PersonMention:
    """One person the extractor found in a post's text.

    Attributes:
        affiliated_organization_names: may be empty (mentioned without a
            stated affiliation) or contain more than one name (the N:N
            case the product requirement describes).
        job_title: the person's title/position as the text states it
            (e.g. "영업팀장," "구매담당"), or ``None`` when the text does
            not say. Two different real people can share a name -- a
            name alone is not a reliable identity key, and dropping a
            stated title would throw away the one signal the text
            offers to tell them apart. Persisted onto
            ``person_affiliation.role_title`` (a schema column that
            already existed, previously never populated) and used by
            ``_upsert_person`` as a same-name disambiguation signal:
            see ``backend/app/keyman_ingestion.py``.
    """

    person_name: str
    person_side_code: str
    affiliated_organization_names: tuple[str, ...] = field(default_factory=tuple)
    job_title: str | None = None


class KeymanExtractionClient(Protocol):
    """Extracts person mentions from a post's title + body."""

    available: bool

    def extract(self, post_title: str, post_body: str) -> list[PersonMention]:
        """Return the people a post's title and body mention.

        Implementations must raise if they cannot extract. Protocol stubs
        raise ``NotImplementedError`` so a no-op body is never treated as
        a successful empty result (a missing signal is not zero mentions).
        """
        raise NotImplementedError


class NullKeymanExtractionClient:
    """No LLM orchestrator configured -- Keyman extraction is unavailable."""

    available = False

    def extract(self, post_title: str, post_body: str) -> list[PersonMention]:
        raise RuntimeError("NullKeymanExtractionClient cannot extract; check .available first")


_EXTRACTION_PROMPT_TEMPLATE = """\
Read the post below and list every named person it mentions. For each
person, classify which side they are on, list every organization they
are affiliated with according to the text (a person may belong to more
than one organization, or none if the text does not say), and give their
job title or position if the text states one. Two different real people
can share the same name -- a stated title/position (e.g. "sales
manager," "purchasing lead") is real evidence for telling them apart, so
report it whenever the text gives one rather than leaving it out.

Reply with ONLY a JSON array (no markdown fences, no prose), where each
element has exactly these fields:
  "name": the person's name as written in the text
  "side": either "our_side" (the post author's own organization/group) or
          "counterparty" (an external customer, partner, competitor, or
          other outside organization)
  "affiliations": a JSON array of organization name strings (can be empty)
  "job_title": the person's stated title/position as a string, or null
               when the text does not give one

If no people are named, reply with an empty JSON array: []

Post title: {title}
Post body: {body}
"""

_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _strip_code_fence(content: str) -> str:
    match = _CODE_FENCE_PATTERN.search(content)
    return match.group(1) if match else content


def parse_keyman_response(content: str) -> list[PersonMention]:
    """Parses the LLM's JSON array response into `PersonMention`s.

    Entries missing a name, or whose "side" isn't one of the two valid
    codes, are skipped rather than guessed at -- a wrong Keyman-side
    classification is worse than a dropped mention, since Phase 2's
    Knowledge Graph edges are typed by this code.
    """
    try:
        parsed = json.loads(_strip_code_fence(content).strip())
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []

    mentions: list[PersonMention] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        side = entry.get("side")
        if not isinstance(name, str) or not name.strip():
            continue
        if side not in _VALID_SIDES:
            continue
        affiliations_raw = entry.get("affiliations") or []
        if not isinstance(affiliations_raw, list):
            affiliations_raw = []
        affiliations = tuple(a.strip() for a in affiliations_raw if isinstance(a, str) and a.strip())
        job_title_raw = entry.get("job_title")
        job_title = job_title_raw.strip() if isinstance(job_title_raw, str) and job_title_raw.strip() else None
        mentions.append(
            PersonMention(
                person_name=name.strip(),
                person_side_code=side,
                affiliated_organization_names=affiliations,
                job_title=job_title,
            )
        )
    return mentions


class ContextualOrchestratorKeymanExtractionClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="route"``."""

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "medium", timeout: float = 60.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def extract(self, post_title: str, post_body: str) -> list[PersonMention]:
        prompt = _EXTRACTION_PROMPT_TEMPLATE.format(title=post_title, body=post_body)
        body = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "messages": [{"role": "user", "content": prompt}],
                "mode": "route",
                "reasoning_effort": self._reasoning_effort,
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        content = body["choices"][0]["message"]["content"]
        return parse_keyman_response(content)
