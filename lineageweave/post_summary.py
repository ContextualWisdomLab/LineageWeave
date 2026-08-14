"""Pluggable Korean summary + key-event + R&R (roles & responsibilities)
derivation for a post -- the popup's summary panel.

Grounded in three distinct extraction tasks, not one undifferentiated
"summarize this" prompt:

- **Summary**: abstractive summarization (See, Liu, & Manning, 2017) --
  a summary is a genuinely re-generated, condensed account, not an
  extracted span of the original text.
- **Key events**: ACE-style event-mention extraction (Doddington et al.,
  2004), the same grounding ``keyman_extraction`` and TEPP's ADR-0016
  three-layer separation already use elsewhere in this repo -- an event
  is a discrete, datable occurrence a reader would want as its own
  bullet, not a summary sentence.
- **R&R (roles & responsibilities)**: semantic role labeling (Gildea &
  Jurafsky, 2002) -- who did what, framed as an agent/action/responsibility
  triple per named actor in the post, not prose. The actor is not always
  a person: business correspondence routinely names an organization
  as the acting party ("당사" [our company], "Demo Corp"), not an
  individual. Modeling every actor as a person loses this distinction
  and makes an organization's affiliation-less name look like an
  unresolved person. Grounded in W3C PROV-O (Lebo, Sahoo, & McGuinness,
  2013): ``prov:Agent`` is the general acting-party class, with
  ``prov:Person`` and ``prov:Organization`` as its two recognized
  subclasses -- the same distinction ``keyman_extraction``'s two-sided
  (our-side/counterparty) person model already keeps for *people*, one
  level up. A person actor also gets an inferred
  ``affiliated_organization_name`` where the text supports it: a bare
  person name without who they work for is hard to place in the same
  way an unresolved organization name is.

Same pluggable-client, never-fake-a-missing-channel discipline as every
other Phase 2/3 channel: :class:`NullPostSummaryClient` makes the channel
unavailable, never invents a summary.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Protocol

from .http_client import post_json

# common_lookup_value category "prov_agent_type" -- PROV-O's prov:Person /
# prov:Organization, the two subclasses of prov:Agent this repo models.
ACTOR_TYPE_PERSON = "prov_person"
ACTOR_TYPE_ORGANIZATION = "prov_organization"
_VALID_ACTOR_TYPE_CODES = frozenset({ACTOR_TYPE_PERSON, ACTOR_TYPE_ORGANIZATION})


@dataclass(frozen=True)
class RoleResponsibility:
    """One actor's role/responsibility as derived from the post text.

    Attributes:
        actor_name: the person's or organization's name as named in the
            text.
        responsibility: what they are responsible for or did.
        actor_type_code: ``ACTOR_TYPE_PERSON`` or ``ACTOR_TYPE_ORGANIZATION``
            (PROV-O ``prov:Person`` / ``prov:Organization``) -- which this
            actor actually is, not assumed to be a person.
        affiliated_organization_name: for a person actor, the
            organization the text says or implies they work for, when
            the text supports it; ``None`` when the text gives no
            affiliation to infer, or for an organization actor (its own
            name already answers "which organization").
    """

    actor_name: str
    responsibility: str
    actor_type_code: str = ACTOR_TYPE_PERSON
    affiliated_organization_name: str | None = None

    def __post_init__(self) -> None:
        if self.actor_type_code not in _VALID_ACTOR_TYPE_CODES:
            raise ValueError(
                f"actor_type_code must be one of {sorted(_VALID_ACTOR_TYPE_CODES)}, "
                f"got {self.actor_type_code!r}"
            )


@dataclass(frozen=True)
class PostSummary:
    """The popup summary panel's full content for one post."""

    korean_summary: str
    key_events: tuple[str, ...] = field(default_factory=tuple)
    roles_and_responsibilities: tuple[RoleResponsibility, ...] = field(default_factory=tuple)


class PostSummaryClient(Protocol):
    """Derives a Korean summary, key events, and R&R from a post's text."""

    available: bool

    def summarize(self, post_title: str, post_body: str) -> PostSummary:
        """Return a Korean summary, key events, and R&R for one post.

        Implementations must raise if they cannot summarize. Protocol
        stubs raise ``NotImplementedError`` so a no-op body is never
        treated as a successful empty result.
        """
        raise NotImplementedError


class NullPostSummaryClient:
    """No LLM orchestrator configured -- summary derivation is unavailable."""

    available = False

    def summarize(self, post_title: str, post_body: str) -> PostSummary:
        raise RuntimeError("NullPostSummaryClient cannot summarize; check .available first")


_SUMMARY_PROMPT_TEMPLATE = """\
Read the post below (it may be in English, Korean, or mixed) and produce
three things:

1. A Korean-language summary (2-4 sentences) of what the post is about --
   genuinely condensed and re-worded, not copied sentences from the text.
2. A list of key events: discrete, datable occurrences mentioned in the
   post (e.g. "a bid was submitted", "a delivery date was confirmed"),
   each as a short phrase.
3. A list of roles & responsibilities: for each named actor in the post
   -- a person OR an organization acting in its own name (e.g. "당사"
   [our company], "Demo Corp") -- one short phrase describing what they
   are responsible for or did, according to the text. Do not force an
   organization's name into a person slot: decide whether each actor is
   a person or an organization, and say which.
   When the actor is a person and the text names or clearly implies who
   they work for, also give that organization's name -- a bare person
   name without their employer is hard to place.

Reply with ONLY a JSON object (no markdown fences, no prose) with exactly
these fields:
  "korean_summary": string
  "key_events": array of strings
  "roles_and_responsibilities": array of objects, each with:
    "actor_name": string
    "responsibility": string
    "actor_type": exactly "person" or "organization"
    "affiliated_organization_name": string, or null when the actor is an
      organization, or when the actor is a person and the text gives no
      affiliation to infer

Post title: {title}
Post body: {body}
"""

_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _strip_code_fence(content: str) -> str:
    match = _CODE_FENCE_PATTERN.search(content)
    return match.group(1) if match else content


def parse_summary_response(content: str) -> PostSummary | None:
    """Parses the LLM's JSON object response into a `PostSummary`.

    Returns `None` (not an empty-but-present summary) if the response
    doesn't have a genuine `korean_summary` string -- a missing summary
    must stay distinguishable from a summary that says nothing, same
    "no fake positive" discipline as every other parser in this repo.
    """
    try:
        parsed = json.loads(_strip_code_fence(content).strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None

    korean_summary = parsed.get("korean_summary")
    if not isinstance(korean_summary, str) or not korean_summary.strip():
        return None

    key_events_raw = parsed.get("key_events") or []
    key_events = tuple(e.strip() for e in key_events_raw if isinstance(e, str) and e.strip()) if isinstance(
        key_events_raw, list
    ) else ()

    rr_raw = parsed.get("roles_and_responsibilities") or []
    roles: list[RoleResponsibility] = []
    if isinstance(rr_raw, list):
        for entry in rr_raw:
            if not isinstance(entry, dict):
                continue
            name = entry.get("actor_name")
            responsibility = entry.get("responsibility")
            actor_type_raw = entry.get("actor_type")
            actor_type_code = (
                ACTOR_TYPE_ORGANIZATION if actor_type_raw == "organization" else ACTOR_TYPE_PERSON
            )
            affiliation_raw = entry.get("affiliated_organization_name")
            affiliated_organization_name = (
                affiliation_raw.strip()
                if isinstance(affiliation_raw, str) and affiliation_raw.strip()
                else None
            )
            if (
                isinstance(name, str)
                and name.strip()
                and isinstance(responsibility, str)
                and responsibility.strip()
            ):
                roles.append(
                    RoleResponsibility(
                        actor_name=name.strip(),
                        responsibility=responsibility.strip(),
                        actor_type_code=actor_type_code,
                        affiliated_organization_name=affiliated_organization_name,
                    )
                )

    return PostSummary(
        korean_summary=korean_summary.strip(),
        key_events=key_events,
        roles_and_responsibilities=tuple(roles),
    )


class ContextualOrchestratorPostSummaryClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="route"``."""

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "medium", timeout: float = 60.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def summarize(self, post_title: str, post_body: str) -> PostSummary:
        prompt = _SUMMARY_PROMPT_TEMPLATE.format(title=post_title, body=post_body)
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
        summary = parse_summary_response(content)
        if summary is None:
            raise ValueError(f"summary response did not match the required format: {content!r}")
        return summary
