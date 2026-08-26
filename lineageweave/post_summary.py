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
from uuid import UUID

from .http_client import chat_completion_content, post_json

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
FIVE_W1H_EVIDENCE_SLOTS = frozenset({"when", "where", "why", "how"})
# Stored rows without this contract version are legacy summaries and must be
# regenerated from the current source body before the popup treats them as evidence.
POST_SUMMARY_CONTRACT_VERSION = 6


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
class MajorEventAction:
    """One source-grounded handoff attached to a major event.

    ``None`` means that the source did not name the requester or processor;
    it is not permission to infer a person from account metadata.
    """

    action_text: str
    requester_actor_name: str | None
    processor_actor_name: str | None
    evidence_text: str
    project_key: str | None = None

    def __post_init__(self) -> None:
        if not self.action_text.strip() or not self.evidence_text.strip():
            raise ValueError("major event actions require action and evidence text")
        for field_name, value in (
            ("requester_actor_name", self.requester_actor_name),
            ("processor_actor_name", self.processor_actor_name),
            ("project_key", self.project_key),
        ):
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} must be non-empty when provided")


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


@dataclass(frozen=True)
class KeyEvent:
    """One source-grounded event, optionally bound to a named project."""

    event_text: str
    project_key: str | None = None

    def __post_init__(self) -> None:
        if not self.event_text.strip():
            raise ValueError("key events require event text")
        if self.project_key is not None and not self.project_key.strip():
            raise ValueError("project_key must be non-empty when provided")


@dataclass(frozen=True)
class FiveW1HEvidence:
    """One explicitly stated 5W1H value and its supporting source phrase."""

    slot_code: str
    value_text: str
    evidence_text: str

    def __post_init__(self) -> None:
        if self.slot_code not in FIVE_W1H_EVIDENCE_SLOTS:
            raise ValueError(f"unsupported 5W1H evidence slot: {self.slot_code!r}")
        if not self.value_text.strip() or not self.evidence_text.strip():
            raise ValueError("5W1H evidence requires a value and supporting text")


def normalize_project_key(project_name: str) -> str:
    """Stable comparison key; raw/canonical labels and evidence stay separate."""
    normalized = unicodedata.normalize("NFKC", project_name).casefold()
    return re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE).strip("-")


def project_candidate_node_id(post_id: str, project_key: str) -> str:
    """Return a post-scoped node id without asserting cross-post identity."""

    canonical_post_id = str(UUID(post_id))
    if not project_key or normalize_project_key(project_key) != project_key:
        raise ValueError("project_key must already be normalized")
    return f"{canonical_post_id}/{project_key}"


def parse_project_candidate_node_id(node_id: str) -> tuple[str, str]:
    """Validate and split one post-scoped unresolved Project candidate id."""

    post_id, separator, project_key = node_id.partition("/")
    if not separator or "/" in project_key:
        raise ValueError("project candidate node id must contain one post/key separator")
    canonical = project_candidate_node_id(post_id, project_key)
    if canonical != node_id:
        raise ValueError("project candidate node id is not canonical")
    return post_id, project_key


def _parse_optional_project_key(value: object) -> str | None:
    """Normalize an explicitly named project, rejecting empty sentinel values."""
    if not isinstance(value, str) or not value.strip():
        return None
    project_key = normalize_project_key(value)
    if project_key in {"", "none", "null", "unknown", "n-a", "na"}:
        return None
    return project_key


@dataclass(frozen=True)
class PostSummary:
    """The popup summary panel's full content for one post."""

    korean_summary: str
    key_events: tuple[str, ...] = field(default_factory=tuple)
    key_event_details: tuple[KeyEvent, ...] = field(default_factory=tuple)
    roles_and_responsibilities: tuple[RoleResponsibility, ...] = field(default_factory=tuple)
    major_event_actions: tuple[MajorEventAction, ...] = field(default_factory=tuple)
    project_mentions: tuple[ProjectMention, ...] = field(default_factory=tuple)
    five_w1h_evidence: tuple[FiveW1HEvidence, ...] = field(default_factory=tuple)


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
five things:

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
   Name every person and organization by their actual stated name whenever the text gives one (e.g. "홍길동 PM, 김철수 PM이 참석했다" instead of a collective "PM들이 참석했다").
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

5. A list of 5W1H evidence items. Explicitly extract specific 'when', 'where', 'why', and 'how' facts from the text. For each fact, return the slot code, the extracted value, and the exact supporting phrase. Do not infer anything not in the text.

Structured context hints (hints, not proof): {context_hints}
Treat a customer value such as 기타, 미등록고객, unknown, or other as a
weak hint; it cannot confirm a project by itself.

Keep the response compact: use at most 5 summary sentences, 6 key events, 8
roles, and 8 project mentions. Keep every event, responsibility, and evidence
phrase short. Return an empty array when the post supports no item.

Reply with ONLY a JSON object (no markdown fences, no prose) with exactly
these fields:
  "korean_summary": string
  "key_events": array of objects, each with:
    "event_text": string,
    "project_name": string (the name of the project this event belongs to, or null if unassigned)
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
  "five_w1h_evidence": array of objects, each with:
    "slot_code": exactly "when", "where", "why", or "how",
    "value_text": string, "evidence_text": string

Post title: {title}
Post body: {body}
"""
_SUMMARY_MAX_TOKENS = 2048

_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

# The full legacy contract remains parseable for persisted/test responses. The
# local provider is more reliable when the two nested-array groups are split.
_SUMMARY_REQUEST_PROMPT_TEMPLATE = """\
Write a concise Korean summary in five to seven complete sentences using
only the evidence below. Weave who, what, when, where, why, and how into
natural flowing prose -- do NOT write a "누가: ... 언제: ... 어디서: ..."
label-value list; that is a table, not a summary. Use "본문에 없음" only
inside a sentence for a dimension the evidence genuinely lacks, never as
a standalone label line. Do not invent facts or a generic report
sentence.

Name every person and organization by their actual stated name whenever
the text gives one. "PM들이 참석했다" ("PMs attended") is not acceptable
when the text names them ("홍길동 PM, 김철수 PM이 참석했다") -- a title-only
collective reference is a lost fact, not an acceptable compression, even
though it costs more words. The same applies to organizations: name the
specific company/team the text gives, not a generic "관계자" or
"업체" placeholder.

Structure the prose as three parts, in order, without labeling them:
1. 발단 (trigger): what event, request, or problem started this post.
2. 전개 (development): what was investigated, discussed, or done as a
   result -- include any option considered, tradeoff weighed, or
   disagreement, not only the final action.
3. 결론 (conclusion): what was decided or concluded, and the next
   action -- who does what next, or what remains open. If the evidence
   states no decision or next step, say so explicitly (e.g. "다음 조치는
   본문에 없음") rather than inventing one.
A reader must be able to tell, from the prose alone, what triggered this
post, what was actually considered, and what was decided or left open --
not just a flat restatement of facts in body order.

If the evidence covers two or more clearly distinct, unrelated matters
(e.g. different projects, different customers, or topics with no shared
thread -- not just one topic told out of order), address each as its own
compact 발단-전개-결론 unit and clearly distinguish them (state which
matter each sentence belongs to) instead of blending them into one
narrative as if they were a single continuous story.

When two or more projects or matters are present, every key event must name
the project or matter it belongs to. Do not emit a generic event such as
"협의 진행" when the source identifies which project was discussed.

Example shape (fictional content, format only):
Acme Electronics 제3공장에서 케이블 배선 설계 누락이 발견되어 2월 12일
기술 회의가 소집되었다. 회의에서 홍길동 PM은 전선관 규격을 그대로 쓸지
재설계할지를 두고 설계팀과 논의했으며, 재설계 시 발생하는 일정 지연이
쟁점이 되었다. 결론적으로 규격은 유지하되 배선 경로만 변경하기로 했고,
설계팀이 다음 주까지 수정 도면을 제출하기로 했다.

Then write a new line beginning KEY EVENTS: followed by up to four short
event phrases separated by semicolons. When a project or matter is named,
write each event as `project canonical key :: event phrase`; use `NONE ::`
only when the event is not attributable to a named project. If the evidence
covers multiple distinct matters, include events from each of them, not only
the first or most prominent one. If there are no events, write NONE.
Context hints are weak evidence only: {context_hints}
Post title: {title}
Post body: {body}
"""

_DETAILS_REQUEST_PROMPT_TEMPLATE = """\
Use only the post evidence below. Do not output analysis or markdown.
Write exactly these four section markers, each on its own line:

ROLES:
<one row per named actor, in this exact column order:>
actor name | responsibility | person, organization, or team | affiliation or NONE

Column 1 is always the actor's own name (a person's name, an organization's
name, or a team's name) -- never a role description or a category label
such as "meeting participant" or "attendee". Column 3 must be exactly one
of the three words person, organization, or team -- never a name. One row
per distinct actor: when several different people share the same
responsibility (e.g. a list of meeting attendees), write one row per
person and repeat the responsibility text on each row rather than merging
them into a single row.

Never write a ROLES row for the account/system identity named in the
context hints (author_account_name, author_account_id, and similar) --
those hints describe who is viewing or importing this record, not a
participant the post text names. Only write a row for that name if the
post title or body independently names that same person doing something
-- an account name appearing only in the hints is not post evidence.

Worked examples (fictional names, format only, not real post's content):
홍길동 | 견적 승인 검토 | person | Acme Electronics
Acme Renewables | 기술 세미나 참석 | organization | NONE
설계팀 | 도면 검토 지원 | team | Acme Electronics

PROJECTS:
project name | canonical name | shortest supporting evidence | confidence from 0 to 1

ACTIONS:
major event or action | project canonical key or NONE | requester actor name or NONE | processor actor name or NONE | shortest supporting evidence

EVIDENCE:
slot (when, where, why, or how) | value stated in the post | shortest supporting phrase

Use NONE on the line after a marker when the evidence supports no item. Keep
each row short. For ACTIONS, the project canonical key must exactly match a
canonical name in PROJECTS or be NONE. Requester and processor must be actor
names also present in ROLES. Use NONE only when the post does not name that
actor. Do not invent actors, projects, affiliations, actions, or confidence.
Only write EVIDENCE rows when the post explicitly supports the value; do not
turn the record's filing timestamp into an event time and do not infer a
place, reason, or method from a title alone.
Treat structured context hints as weak priors, not facts. A customer value
such as 기타, 미등록고객, unknown, or other cannot confirm a project by itself.
Field roles are strict: source_business_unit_code and
source_process_unit_name are PU/business-unit hints only and must never be
used as a sales-pool/order-pool value. source_sales_pool_code and
source_sales_pool_name are sales-pool/order-pool hints only and must never be
used as a PU/business-unit value. Source project fields remain project hints,
not catalog bindings, unless the post evidence supports them.
Post title: {title}
Post body: {body}
Context hints: {context_hints}
"""


def _strip_code_fence(content: str) -> str:
    """Implement the _strip_code_fence operation for this channel."""
    match = _CODE_FENCE_PATTERN.search(content)
    return match.group(1) if match else content


def _parse_plain_summary_response(
    content: str,
) -> tuple[str, tuple[str, ...], tuple[KeyEvent, ...]] | None:
    """Parse the provider-compatible plain summary and event marker."""
    plain = _strip_code_fence(content).strip()
    match = re.search(r"(?im)^\s*KEY EVENTS\s*:\s*", plain)
    if match is None:
        return (plain, ()) if plain else None
    summary = plain[: match.start()].strip()
    raw_events = plain[match.end() :].strip()
    events: list[str] = []
    details: list[KeyEvent] = []
    for raw_event in re.split(r";|\n", raw_events):
        event = raw_event.strip(" -*\t")
        if not event or event.upper() == "NONE":
            continue
        if "::" in event:
            project_raw, event_text = (part.strip() for part in event.split("::", 1))
            event_text = event_text.strip(" -*\t")
            project_key = _parse_optional_project_key(project_raw)
        else:
            event_text = event
            project_key = None
        if not event_text or event_text.upper() == "NONE":
            continue
        events.append(event_text)
        details.append(KeyEvent(event_text=event_text, project_key=project_key))
    return (summary, tuple(events), tuple(details)) if summary else None


_HINT_VALUE_PATTERN = re.compile(r"(?:^|;)\s*author_account_name=([^;\[]+?)\s*(?:\[|;|$)")


def _hallucinated_account_name(context_hints: str) -> str | None:
    """The logged-in account's display name, if the hint string carries one.

    Live finding (2026-08-19): the model twice wrote a ROLES row for
    this exact value -- e.g. "Demo Analyst | 발주처 면담 및 대책 협의 |
    person | Demo Corp" -- even though that name never appears in the
    post body. author_account_name describes who is viewing/importing
    the record, not a participant named in the text; the prompt now says
    so explicitly, but this is the belt-and-suspenders check since a
    fabricated actor with a fabricated responsibility is worse than a
    dropped one.
    """
    match = _HINT_VALUE_PATTERN.search(context_hints)
    return match.group(1).strip() if match else None


def _parse_plain_summary_details(
    content: str,
    *,
    post_title: str = "",
    context_hints: str = "",
) -> tuple[
    tuple[RoleResponsibility, ...],
    tuple[ProjectMention, ...],
    tuple[MajorEventAction, ...],
    tuple[FiveW1HEvidence, ...],
] | None:
    """Parse the compact semantic extraction contract without nested JSON."""
    plain = _strip_code_fence(content).strip()
    markers = list(re.finditer(r"(?im)^\s*(ROLES|PROJECTS|ACTIONS|EVIDENCE)\s*:\s*(.*)$", plain))
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
    # The model occasionally echoes _DETAILS_REQUEST_PROMPT_TEMPLATE's own
    # column-header line or one of its worked-example rows back verbatim
    # as if it were a data row. These would otherwise usually get dropped
    # by the actor_type lookup below anyway (their 3rd column doesn't say
    # "person"/"organization"/"team"), but that is an accident of their
    # specific wording, not a real filter -- skip them by exact match so
    # the intent is explicit and doesn't depend on that accident holding
    # for every future prompt edit.
    _template_echo_rows = frozenset(
        row.casefold()
        for row in (
            "actor name | responsibility | person, organization, or team | affiliation or none",
            "홍길동 | 견적 승인 검토 | person | acme electronics",
            "acme renewables | 기술 세미나 참석 | organization | none",
            "설계팀 | 도면 검토 지원 | team | acme electronics",
        )
    )
    hallucinated_account_name = _hallucinated_account_name(context_hints)
    roles: list[RoleResponsibility] = []
    for raw_row in sections["ROLES"].splitlines():
        row = raw_row.strip().lstrip("-* ").strip()
        if not row or row.casefold() in empty_values or row.casefold() in _template_echo_rows:
            continue
        parts = [part.strip() for part in row.split("|", 3)]
        if len(parts) == 3:
            actor_name, responsibility, affiliation = parts
            actor_type = "person"
        elif len(parts) == 4:
            actor_name, responsibility, actor_type, affiliation = parts
        else:
            continue
        if (
            hallucinated_account_name is not None
            and actor_name.casefold() == hallucinated_account_name.casefold()
        ):
            continue
        actor_type_code = {
            "person": ACTOR_TYPE_PERSON,
            "organization": ACTOR_TYPE_ORGANIZATION,
            "team": ACTOR_TYPE_TEAM,
            ACTOR_TYPE_PERSON: ACTOR_TYPE_PERSON,
            ACTOR_TYPE_ORGANIZATION: ACTOR_TYPE_ORGANIZATION,
            ACTOR_TYPE_TEAM: ACTOR_TYPE_TEAM,
        }.get(actor_type.casefold())
        # A row whose 3rd column isn't literally person/organization/team is
        # not recoverable by reshuffling columns: nothing here tells us
        # which of the other 3 fields actually holds the real actor name
        # (see the 2026-08-19 live finding where the model put a
        # description like "Q&A participant" in column 1 and the real
        # name in column 3 for a run of grouped meeting-attendee rows).
        # Guessing would risk cataloging a role description as a person's
        # name. Dropping the row is the same "no fake positive" discipline
        # this module already documents for a missing summary -- if this
        # keeps recurring after the worked examples above, the fix is a
        # better prompt/model, not a column-guessing heuristic here.
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
    actions: list[MajorEventAction] = []
    role_names = {role.actor_name.casefold() for role in roles}

    def _is_actor_field(value: str) -> bool:
        """Recognize the actor columns required by the five-column contract."""
        return value.casefold() in empty_values or value.casefold() in role_names

    for raw_row in sections.get("ACTIONS", "").splitlines():
        row = raw_row.strip().lstrip("-* ").strip()
        if not row or row.casefold() in empty_values:
            continue
        parts = [part.strip() for part in row.split("|", 4)]
        if len(parts) == 5 and _is_actor_field(parts[2]) and _is_actor_field(parts[3]):
            action_text, project_key_raw, requester, processor, evidence_text = parts
            project_key = _parse_optional_project_key(project_key_raw)
        else:
            legacy_parts = [part.strip() for part in row.split("|", 3)]
            if len(legacy_parts) != 4:
                continue
            action_text, requester, processor, evidence_text = legacy_parts
            project_key = None
        if not action_text:
            continue
        if evidence_text.casefold() in empty_values:
            continue
        requester_name = None if requester.casefold() in empty_values else requester
        processor_name = None if processor.casefold() in empty_values else processor
        try:
            actions.append(
                MajorEventAction(
                    action_text=action_text,
                    requester_actor_name=requester_name,
                    processor_actor_name=processor_name,
                    evidence_text=evidence_text,
                    project_key=project_key,
                )
            )
        except ValueError:
            continue

    evidence: list[FiveW1HEvidence] = []
    for raw_row in sections.get("EVIDENCE", "").splitlines():
        row = raw_row.strip().lstrip("-* ").strip()
        if not row or row.casefold() in empty_values:
            continue
        parts = [part.strip() for part in row.split("|", 2)]
        if len(parts) != 3 or parts[0].casefold() not in FIVE_W1H_EVIDENCE_SLOTS:
            continue
        try:
            evidence.append(FiveW1HEvidence(parts[0].casefold(), parts[1], parts[2]))
        except ValueError:
            continue
    return tuple(roles), tuple(projects), tuple(actions), tuple(evidence)


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
    key_events: list[str] = []
    key_event_details: list[KeyEvent] = []
    if isinstance(key_events_raw, list):
        for entry in key_events_raw:
            if isinstance(entry, str) and entry.strip():
                parsed_event = _parse_plain_summary_response(f"summary\nKEY EVENTS: {entry}")
                if parsed_event is not None:
                    _summary, events, details = parsed_event
                    key_events.extend(events)
                    key_event_details.extend(details)
            elif isinstance(entry, dict):
                event_text = entry.get("event_text") or entry.get("event")
                if not isinstance(event_text, str) or not event_text.strip():
                    continue
                project_key = _parse_optional_project_key(
                    entry.get("project_key") or entry.get("project_name")
                )
                try:
                    detail = KeyEvent(event_text=event_text.strip(), project_key=project_key)
                except ValueError:
                    continue
                key_events.append(detail.event_text)
                key_event_details.append(detail)

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

    actions: list[MajorEventAction] = []
    raw_actions = parsed.get("major_event_actions") or parsed.get("actions") or []
    if isinstance(raw_actions, list):
        for entry in raw_actions:
            if not isinstance(entry, dict):
                continue
            action_text = entry.get("action_text") or entry.get("event_text")
            evidence_text = entry.get("evidence_text") or entry.get("evidence")
            requester = entry.get("requester_actor_name")
            processor = entry.get("processor_actor_name")
            project_key = _parse_optional_project_key(
                entry.get("project_key") or entry.get("project_name")
            )
            if not isinstance(action_text, str) or not isinstance(evidence_text, str):
                continue
            requester_name = requester.strip() if isinstance(requester, str) and requester.strip() else None
            processor_name = processor.strip() if isinstance(processor, str) and processor.strip() else None
            try:
                actions.append(
                    MajorEventAction(
                        action_text=action_text.strip(),
                        requester_actor_name=requester_name,
                        processor_actor_name=processor_name,
                        evidence_text=evidence_text.strip(),
                        project_key=project_key,
                    )
                )
            except ValueError:
                continue

    five_w1h_raw = parsed.get("five_w1h_evidence") or parsed.get("evidence") or []
    five_w1h_evidence: list[FiveW1HEvidence] = []
    if isinstance(five_w1h_raw, list):
        for entry in five_w1h_raw:
            if not isinstance(entry, dict):
                continue
            try:
                five_w1h_evidence.append(
                    FiveW1HEvidence(
                        str(entry.get("slot_code", "")).strip().casefold(),
                        str(entry.get("value_text", "")).strip(),
                        str(entry.get("evidence_text", "")).strip(),
                    )
                )
            except ValueError:
                continue

    return PostSummary(
        korean_summary=korean_summary.strip(),
        key_events=tuple(key_events),
        key_event_details=tuple(key_event_details),
        roles_and_responsibilities=tuple(roles),
        major_event_actions=tuple(actions),
        project_mentions=tuple(project_mentions),
        five_w1h_evidence=tuple(five_w1h_evidence),
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
    """Derive summary and semantic evidence through two ``mode="auto"`` calls."""

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "auto", timeout: float = 180.0
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
                "mode": "auto",
                "reasoning_effort": self._reasoning_effort,
                "max_tokens": _SUMMARY_MAX_TOKENS,
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        content = chat_completion_content(body)
        parsed = _parse_plain_summary_response(content)
        if parsed is None:
            raise ValueError("summary response did not match the required format")
        korean_summary, key_events, key_event_details = parsed
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
                "mode": "auto",
                "reasoning_effort": self._reasoning_effort,
                "max_tokens": _SUMMARY_MAX_TOKENS,
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        details_content = chat_completion_content(details_body)
        details = _parse_plain_summary_details(
            details_content,
            post_title=post_title,
            context_hints=context_hints,
        )
        if details is None:
            raise ValueError("summary semantic response did not match the required format")
        roles, projects, actions, five_w1h_evidence = details
        return PostSummary(
            korean_summary=korean_summary,
            key_events=key_events,
            key_event_details=key_event_details,
            roles_and_responsibilities=roles,
            major_event_actions=actions,
            project_mentions=projects,
            five_w1h_evidence=five_w1h_evidence,
        )
