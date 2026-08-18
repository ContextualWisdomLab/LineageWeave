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
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

from .http_client import post_json

# common_lookup_value category "prov_agent_type" -- PROV-O's prov:Person /
# prov:Organization for the micro/macro cases, plus a meso-level third
# case this repo's own real data needed: a named sub-unit of a company
# ("설계팀" / "design team"), which is neither a person nor the company
# itself. Grounded in the W3C Organization Ontology's org:OrganizationalUnit
# (Reynolds, 2014), not invented -- see docs/adr/0007-team-actor-type.md.
ACTOR_TYPE_PERSON = "prov_person"
ACTOR_TYPE_ORGANIZATION = "prov_organization"
ACTOR_TYPE_TEAM = "prov_team"
_VALID_ACTOR_TYPE_CODES = frozenset({ACTOR_TYPE_PERSON, ACTOR_TYPE_ORGANIZATION, ACTOR_TYPE_TEAM})
PROJECT_MENTION_CONFIDENCE_THRESHOLD = 0.7
# Stored rows without this contract version are legacy summaries and must be
# regenerated from the current source body before the popup treats them as evidence.
POST_SUMMARY_CONTRACT_VERSION = 2


@dataclass(frozen=True)
class RoleResponsibility:
    """One actor's role/responsibility as derived from the post text.

    Attributes:
        actor_name: the person's or organization's name as named in the
            text.
        responsibility: what they are responsible for or did.
        actor_type_code: ``ACTOR_TYPE_PERSON``, ``ACTOR_TYPE_ORGANIZATION``,
            or ``ACTOR_TYPE_TEAM`` (PROV-O ``prov:Person`` /
            ``prov:Organization``, or the meso-level
            ``org:OrganizationalUnit`` for a named sub-unit like "설계팀")
            -- which this actor actually is, not assumed to be a person.
        affiliated_organization_name: for a person OR team actor, the
            organization the text says or implies they belong to, when
            the text supports it; ``None`` when the text gives no
            affiliation to infer, or for an organization actor (its own
            name already answers "which organization"). A team actor
            without this is an unplaced team -- the text should usually
            support it since a team is always someone's team.
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
class ProjectMention:
    """One project supported by post text and semantic context."""

    project_name: str
    canonical_name: str
    evidence: str
    confidence: float

    def __post_init__(self) -> None:
        if not self.project_name.strip() or not self.canonical_name.strip() or not self.evidence.strip():
            raise ValueError("project mentions require names and evidence")
        if not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("project mention confidence must be between 0 and 1")


def normalize_project_key(project_name: str) -> str:
    """Stable comparison key; raw/canonical labels and evidence stay separate."""
    normalized = unicodedata.normalize("NFKC", project_name).casefold()
    return re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE).strip("-")


@dataclass(frozen=True)
class PostSummary:
    """The popup summary panel's full content for one post."""

    korean_summary: str
    key_events: tuple[str, ...] = field(default_factory=tuple)
    roles_and_responsibilities: tuple[RoleResponsibility, ...] = field(default_factory=tuple)
    project_mentions: tuple[ProjectMention, ...] = field(default_factory=tuple)


class PostSummaryClient(Protocol):
    """Derives summary, R&R, and evidence-backed project mentions."""

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
        """Summarize the post and extract its supported semantic signals."""
        raise RuntimeError("NullPostSummaryClient cannot summarize; check .available first")

    def summarize_with_hints(
        self, post_title: str, post_body: str, context_hints: str
    ) -> PostSummary:
        """Summarize the post while using contextual hints as non-authoritative priors."""
        raise RuntimeError("NullPostSummaryClient cannot summarize; check .available first")


_SUMMARY_PROMPT_TEMPLATE = """\
Read the post below (it may be in English, Korean, or mixed) and produce
four things:

Do not output a reasoning trace. Return the JSON object immediately.

1. A Korean-language, evidence-grounded summary in 3-5 sentences. It must
   answer the supported parts of 5W1H: who acted, what happened, when and
   where it happened, why or what goal was involved, and how it progressed or
   what happens next. If a dimension is absent from the post, say "본문에
   없음" rather than inventing it. Do not write a generic sentence such as
   "이 게시물은 ... 보고를 담고 있다" when the body contains more detail.
2. A list of key events: discrete occurrences mentioned in the post (e.g.
   "a bid was submitted", "a delivery date was confirmed"), each as a short
   phrase with the actor, action, time/place, or result when the body states
   it.
3. A list of roles & responsibilities: for each named actor in the post
   -- a person, an organization acting in its own name (e.g. "당사"
   [our company], "Demo Corp"), OR a named team/department inside an
   organization (e.g. "설계팀" [design team], "Sales Team") -- one short
   phrase describing what they are responsible for or did, according to
   the text. Do not force an organization's name into a person slot, and
   do not force a team's name into an organization slot: a team is a
   sub-unit of a company, not the company itself -- decide which of the
   three each actor is, and say which.
   When the actor is a person and the text names or clearly implies who
   they work for, also give that organization's name -- a bare person
   name without their employer is hard to place. When the actor is a
   team, also give the organization it belongs to (a team is always part
   of some company, even when the text only names the team, e.g. a
   Korean company's internal 설계팀 -- infer the parent company from
   context when the text supports it).

4. A list of project mentions. A project may be stated directly in the
   post body/title or described indirectly in a way supported by the
   structured hints below. For each candidate return the name as written,
   a canonical comparison name, the shortest supporting evidence phrase,
   and a confidence from 0 to 1. Do not invent a project from a generic
   topic. Keep ambiguous candidates with confidence below 0.7 so the UI can
   show uncertainty, but they must not be used as a report grouping.

Structured context hints (hints, not proof): {context_hints}
Treat a customer value such as 기타, 미등록고객, unknown, or other as a
weak hint; it cannot confirm a project by itself.

Keep the response compact: use at most 5 summary sentences, 6 key events, 8
roles, and 8 project mentions. Keep every event, responsibility, and evidence
phrase short. Return an empty array when the post supports no item.

Reply with ONLY a JSON object (no markdown fences, no prose) with exactly
these fields:
  "korean_summary": string
  "key_events": array of strings
  "roles_and_responsibilities": array of objects, each with:
    "actor_name": string
    "responsibility": string
    "actor_type": exactly "person", "organization", or "team"
    "affiliated_organization_name": string, or null when the actor is an
      organization, or when the text gives no affiliation to infer for a
      person or team actor
  "project_mentions": array of objects, each with:
    "project_name": string, "canonical_name": string, "evidence": string,
    "confidence": number

Post title: {title}
Post body: {body}
"""

_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

# The full legacy contract remains parseable for persisted/test responses. The
# local provider is more reliable when the two nested-array groups are split.
_SUMMARY_REQUEST_PROMPT_TEMPLATE = """\
Write a concise Korean 5W1H summary in at most four sentences using only
the evidence below. State who, what, when, where, why, and how when
supported; write "본문에 없음" for a missing dimension. Do not invent
facts or a generic report sentence.

Then write a new line beginning KEY EVENTS: followed by up to four short
event phrases separated by semicolons. If there are no events, write NONE.
Context hints are weak evidence only: {context_hints}
Post title: {title}
Post body: {body}
"""

_DETAILS_REQUEST_PROMPT_TEMPLATE = """\
Use only the post evidence below. Do not output analysis or markdown.
Write exactly these two section markers, each on its own line:

ROLES:
actor | responsibility | person, organization, or team | affiliation or NONE

PROJECTS:
project name | canonical name | shortest supporting evidence | confidence from 0 to 1

Use NONE on the line after a marker when the evidence supports no item. Keep
each row short. Do not invent actors, projects, affiliations, or confidence.
Treat structured context hints as weak priors, not facts. A customer value
such as 기타, 미등록고객, unknown, or other cannot confirm a project by itself.
Post title: {title}
Post body: {body}
Context hints: {context_hints}
"""


def _strip_code_fence(content: str) -> str:
    """Implement the _strip_code_fence operation for this channel."""
    match = _CODE_FENCE_PATTERN.search(content)
    return match.group(1) if match else content


def _parse_plain_summary_response(content: str) -> tuple[str, tuple[str, ...]] | None:
    """Parse the provider-compatible plain summary and event marker."""
    plain = _strip_code_fence(content).strip()
    match = re.search(r"(?im)^\s*KEY EVENTS\s*:\s*", plain)
    if match is None:
        return (plain, ()) if plain else None
    summary = plain[: match.start()].strip()
    raw_events = plain[match.end() :].strip()
    events = tuple(
        event.strip(" -*\t")
        for event in re.split(r";|\n", raw_events)
        if event.strip(" -*\t") and event.strip(" -*\t").upper() != "NONE"
    )
    return (summary, events) if summary else None


def _parse_plain_summary_details(
    content: str,
    *,
    post_title: str = "",
) -> tuple[tuple[RoleResponsibility, ...], tuple[ProjectMention, ...]] | None:
    """Parse the compact semantic extraction contract without nested JSON."""
    plain = _strip_code_fence(content).strip()
    markers = list(re.finditer(r"(?im)^\s*(ROLES|PROJECTS)\s*:\s*(.*)$", plain))
    if not markers:
        return None

    sections: dict[str, str] = {}
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(plain)
        inline = marker.group(2).strip()
        body = plain[marker.end() : end].strip()
        sections[marker.group(1).upper()] = "\n".join(part for part in (inline, body) if part)
    if "ROLES" not in sections or "PROJECTS" not in sections:
        return None

    empty_values = frozenset({"", "none", "null", "n/a", "unknown", "없음", "미상"})
    roles: list[RoleResponsibility] = []
    for raw_row in sections["ROLES"].splitlines():
        row = raw_row.strip().lstrip("-* ").strip()
        if not row or row.casefold() in empty_values:
            continue
        parts = [part.strip() for part in row.split("|", 3)]
        if len(parts) == 3:
            actor_name, responsibility, affiliation = parts
            actor_type = "person"
        elif len(parts) == 4:
            actor_name, responsibility, actor_type, affiliation = parts
        else:
            continue
        actor_type_code = {
            "person": ACTOR_TYPE_PERSON,
            "organization": ACTOR_TYPE_ORGANIZATION,
            "team": ACTOR_TYPE_TEAM,
            ACTOR_TYPE_PERSON: ACTOR_TYPE_PERSON,
            ACTOR_TYPE_ORGANIZATION: ACTOR_TYPE_ORGANIZATION,
            ACTOR_TYPE_TEAM: ACTOR_TYPE_TEAM,
        }.get(actor_type.casefold())
        if not actor_type_code or not actor_name or not responsibility:
            continue
        roles.append(
            RoleResponsibility(
                actor_name=actor_name,
                responsibility=responsibility,
                actor_type_code=actor_type_code,
                affiliated_organization_name=(
                    None if affiliation.casefold() in empty_values else affiliation
                ),
            )
        )

    projects: list[ProjectMention] = []
    for raw_row in sections["PROJECTS"].splitlines():
        row = raw_row.strip().lstrip("-* ").strip()
        if not row or row.casefold() in empty_values:
            continue
        parts = [part.strip() for part in row.split("|", 3)]
        if len(parts) == 3:
            project_name, evidence, confidence_raw = parts
            canonical_name = normalize_project_key(project_name)
        elif len(parts) == 4:
            project_name, canonical_name, evidence, confidence_raw = parts
        else:
            continue
        if evidence.casefold() in empty_values:
            title = post_title.strip()
            if not title or project_name.casefold() not in title.casefold():
                continue
            evidence = title
        try:
            confidence = float(confidence_raw)
            projects.append(
                ProjectMention(
                    project_name=project_name,
                    canonical_name=canonical_name,
                    evidence=evidence,
                    confidence=confidence,
                )
            )
        except (TypeError, ValueError):
            continue
    return tuple(roles), tuple(projects)


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
            if actor_type_raw == "organization":
                actor_type_code = ACTOR_TYPE_ORGANIZATION
            elif actor_type_raw == "team":
                actor_type_code = ACTOR_TYPE_TEAM
            else:
                actor_type_code = ACTOR_TYPE_PERSON
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

    project_mentions_raw = parsed.get("project_mentions") or []
    project_mentions: list[ProjectMention] = []
    if isinstance(project_mentions_raw, list):
        for entry in project_mentions_raw:
            if not isinstance(entry, dict):
                continue
            project_name = entry.get("project_name")
            canonical_name = entry.get("canonical_name")
            evidence = entry.get("evidence")
            confidence = entry.get("confidence")
            if not (
                isinstance(project_name, str)
                and isinstance(canonical_name, str)
                and isinstance(evidence, str)
                and isinstance(confidence, (int, float))
                and not isinstance(confidence, bool)
            ):
                continue
            try:
                project_mentions.append(
                    ProjectMention(
                        project_name=project_name.strip(),
                        canonical_name=canonical_name.strip(),
                        evidence=evidence.strip(),
                        confidence=float(confidence),
                    )
                )
            except ValueError:
                continue

    return PostSummary(
        korean_summary=korean_summary.strip(),
        key_events=key_events,
        roles_and_responsibilities=tuple(roles),
        project_mentions=tuple(project_mentions),
    )


def _parse_summary_details(
    content: str,
) -> tuple[tuple[RoleResponsibility, ...], tuple[ProjectMention, ...]]:
    """Parse compact string-array details without nested JSON objects."""
    try:
        parsed = json.loads(_strip_code_fence(content).strip())
    except json.JSONDecodeError:
        return (), ()
    if not isinstance(parsed, dict):
        return (), ()

    roles: list[RoleResponsibility] = []
    raw_roles = parsed.get("roles") or parsed.get("roles_and_responsibilities") or []
    if isinstance(raw_roles, list):
        for entry in raw_roles:
            if isinstance(entry, dict):
                name = entry.get("actor_name")
                responsibility = entry.get("responsibility")
                actor_type = entry.get("actor_type", "person")
                affiliation = entry.get("affiliated_organization_name")
            elif isinstance(entry, str):
                parts = [part.strip() for part in entry.split("|", 3)]
                if len(parts) != 4:
                    continue
                name, responsibility, actor_type, affiliation = parts
            else:
                continue
            if not isinstance(name, str) or not isinstance(responsibility, str):
                continue
            actor_type_code = {
                "organization": ACTOR_TYPE_ORGANIZATION,
                "team": ACTOR_TYPE_TEAM,
            }.get(str(actor_type).strip().lower(), ACTOR_TYPE_PERSON)
            affiliation_text = affiliation.strip() if isinstance(affiliation, str) else ""
            if affiliation_text.casefold() in {"", "none", "null", "없음"}:
                affiliation_text = None
            if name.strip() and responsibility.strip():
                roles.append(
                    RoleResponsibility(
                        actor_name=name.strip(),
                        responsibility=responsibility.strip(),
                        actor_type_code=actor_type_code,
                        affiliated_organization_name=affiliation_text,
                    )
                )

    projects: list[ProjectMention] = []
    raw_projects = parsed.get("projects") or parsed.get("project_mentions") or []
    if isinstance(raw_projects, list):
        for entry in raw_projects:
            if isinstance(entry, dict):
                values = (
                    entry.get("project_name"),
                    entry.get("canonical_name"),
                    entry.get("evidence"),
                    entry.get("confidence"),
                )
            elif isinstance(entry, str):
                parts = [part.strip() for part in entry.split("|", 3)]
                if len(parts) != 4:
                    continue
                values = (*parts[:3], parts[3])
            else:
                continue
            project_name, canonical_name, evidence, confidence = values
            if not all(isinstance(value, str) for value in (project_name, canonical_name, evidence)):
                continue
            try:
                projects.append(
                    ProjectMention(
                        project_name=project_name.strip(),
                        canonical_name=canonical_name.strip(),
                        evidence=evidence.strip(),
                        confidence=float(confidence),
                    )
                )
            except (TypeError, ValueError):
                continue
    return tuple(roles), tuple(projects)


class ContextualOrchestratorPostSummaryClient:
    """Derive summary and semantic evidence through two ``mode="route"`` calls."""

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "none", timeout: float = 60.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def summarize(self, post_title: str, post_body: str) -> PostSummary:
        """Summarize the post and extract its supported semantic signals."""
        return self.summarize_with_hints(post_title, post_body, "")

    def summarize_with_hints(
        self, post_title: str, post_body: str, context_hints: str
    ) -> PostSummary:
        """Summarize the post while using contextual hints as non-authoritative priors."""
        prompt = _SUMMARY_REQUEST_PROMPT_TEMPLATE.format(
            title=post_title,
            body=post_body,
            context_hints=context_hints.strip() or "none available",
        )
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
        parsed = _parse_plain_summary_response(content)
        if parsed is None:
            raise ValueError(f"summary response did not match the required format: {content!r}")
        korean_summary, key_events = parsed
        details_body = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "messages": [
                    {
                        "role": "user",
                        "content": _DETAILS_REQUEST_PROMPT_TEMPLATE.format(
                            title=post_title,
                            body=post_body,
                            context_hints=context_hints.strip() or "none available",
                        ),
                    }
                ],
                "mode": "route",
                "reasoning_effort": self._reasoning_effort,
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        details = _parse_plain_summary_details(
            details_body["choices"][0]["message"]["content"],
            post_title=post_title,
        )
        if details is None:
            raise ValueError(
                "summary semantic response did not match the required format: "
                f"{details_body['choices'][0]['message']['content']!r}"
            )
        roles, projects = details
        return PostSummary(
            korean_summary=korean_summary,
            key_events=key_events,
            roles_and_responsibilities=roles,
            project_mentions=projects,
        )
