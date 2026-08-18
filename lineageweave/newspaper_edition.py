"""Scheduled weekly/monthly newspaper editions for 게시판.

A scheduler assembles each edition from consumed fast-mlsirm member
ranks and Orgmetra grains, then publishes it as a board post. This
module does not fit IRT, leftover maps, RankWeave, or invent a theta.
It does not plant an org-chart. Buyer chrome never calls it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
from typing import Literal

from .orgmetra_client import (
    ORGMETRA_UNAVAILABLE_NEXT_ACTION,
    OrgmetraClient,
    OrgmetraGrain,
    OrgmetraUnit,
)

EditionKind = Literal["week", "month"]

NEWSPAPER_WEEK_KEY = "newspaper-week"
NEWSPAPER_MONTH_KEY = "newspaper-month"
NEWSPAPER_THREAD_KEYS = frozenset({NEWSPAPER_WEEK_KEY, NEWSPAPER_MONTH_KEY})

WEEK_EMPTY_NEXT_ACTION = "이번 주 신문을 아직 받을 수 없습니다"
MONTH_EMPTY_NEXT_ACTION = "이번 달 신문을 아직 받을 수 없습니다"

REPORT_GROUPING_FOR_GRAIN: dict[OrgmetraGrain, str | None] = {
    "corporate": "corporate_entity",
    "process_unit": "process_unit",
    "team": None,
}

GRAIN_SECTION_LABEL: dict[OrgmetraGrain, str] = {
    "corporate": "Corporate",
    "process_unit": "PU",
    "team": "Team",
}


@dataclass(frozen=True)
class NewspaperSection:
    grain_code: OrgmetraGrain
    unit_id: str
    unit_label: str
    titles: tuple[str, ...]
    empty_next_action: str | None


@dataclass(frozen=True)
class NewspaperEdition:
    kind: EditionKind
    period_code: str
    sections: tuple[NewspaperSection, ...]
    empty_next_action: str | None


def newspaper_thread_key(kind: EditionKind) -> str:
    return NEWSPAPER_WEEK_KEY if kind == "week" else NEWSPAPER_MONTH_KEY


def newspaper_title(kind: EditionKind, period_code: str) -> str:
    prefix = "주간 신문" if kind == "week" else "월간 신문"
    return f"{prefix} {period_code}"


def edition_empty_next_action(kind: EditionKind) -> str:
    return WEEK_EMPTY_NEXT_ACTION if kind == "week" else MONTH_EMPTY_NEXT_ACTION


def is_newspaper_thread(thread_group_key: str) -> bool:
    return thread_group_key in NEWSPAPER_THREAD_KEYS


def select_orgmetra_units(client: OrgmetraClient, grain: OrgmetraGrain) -> tuple[OrgmetraUnit, ...]:
    if not client.available:
        return ()
    return client.list_units(grain)


def assemble_newspaper_edition(
    *,
    kind: EditionKind,
    period_code: str,
    orgmetra: OrgmetraClient,
    ranked_titles_by_unit: dict[tuple[OrgmetraGrain, str], Sequence[str]],
) -> NewspaperEdition:
    """Build one edition from consumed ranks + Orgmetra units.

    Missing Orgmetra or an empty consumed rank list fail-closes. Titles
    must already be ordered by the persisted fast-mlsirm member rank.
    """
    if not orgmetra.available:
        return NewspaperEdition(
            kind=kind,
            period_code=period_code,
            sections=(),
            empty_next_action=ORGMETRA_UNAVAILABLE_NEXT_ACTION,
        )
    sections: list[NewspaperSection] = []
    for grain in GRAIN_SECTION_LABEL:
        units = select_orgmetra_units(orgmetra, grain)
        if not units:
            sections.append(
                NewspaperSection(
                    grain_code=grain,
                    unit_id="",
                    unit_label="",
                    titles=(),
                    empty_next_action=ORGMETRA_UNAVAILABLE_NEXT_ACTION,
                )
            )
            continue
        grouping = REPORT_GROUPING_FOR_GRAIN[grain]
        for unit in units:
            titles = tuple(ranked_titles_by_unit.get((grain, unit.unit_id), ()))
            if grouping is None:
                titles = ()
            sections.append(
                NewspaperSection(
                    grain_code=grain,
                    unit_id=unit.unit_id,
                    unit_label=unit.unit_label,
                    titles=titles,
                    empty_next_action=None if titles else edition_empty_next_action(kind),
                )
            )
    if not any(section.titles for section in sections):
        return NewspaperEdition(
            kind=kind,
            period_code=period_code,
            sections=tuple(sections),
            empty_next_action=edition_empty_next_action(kind),
        )
    return NewspaperEdition(
        kind=kind,
        period_code=period_code,
        sections=tuple(sections),
        empty_next_action=None,
    )


def render_newspaper_html(edition: NewspaperEdition) -> str:
    """Buyer-facing newspaper HTML. Never includes a theta."""
    parts = [
        f'<article class="newspaper-edition" data-kind="{escape(edition.kind)}" '
        f'data-period="{escape(edition.period_code)}">'
    ]
    if edition.empty_next_action and not any(section.titles for section in edition.sections):
        parts.append(f'<p class="newspaper-empty">{escape(edition.empty_next_action)}</p>')
    else:
        for section in edition.sections:
            label = GRAIN_SECTION_LABEL[section.grain_code]
            heading = f"{label} · {section.unit_label}" if section.unit_label else label
            parts.append(
                f'<section data-grain="{escape(section.grain_code)}">'
                f"<h2>{escape(heading)}</h2>"
            )
            if section.titles:
                parts.append("<ul>")
                parts.extend(f"<li>{escape(title)}</li>" for title in section.titles)
                parts.append("</ul>")
            elif section.empty_next_action:
                parts.append(f'<p class="newspaper-empty">{escape(section.empty_next_action)}</p>')
            parts.append("</section>")
    parts.append("</article>")
    return "".join(parts)


def edition_payload(edition: NewspaperEdition) -> dict[str, object]:
    """List/detail JSON for a published newspaper post. No theta."""
    return {
        "kind": edition.kind,
        "period_code": edition.period_code,
        "sections": [
            {
                "grain_code": section.grain_code,
                "unit_id": section.unit_id,
                "unit_label": section.unit_label,
                "titles": list(section.titles),
                "empty_next_action": section.empty_next_action,
            }
            for section in edition.sections
        ],
        "empty_next_action": edition.empty_next_action,
    }


class SeedOrgmetraClient:
    """Seed/test double. Production chrome uses ``build_orgmetra_client``."""

    available = True

    def __init__(self, units: Sequence[OrgmetraUnit]) -> None:
        self._units = tuple(units)

    def list_units(self, grain: OrgmetraGrain) -> tuple[OrgmetraUnit, ...]:
        return tuple(unit for unit in self._units if unit.grain_code == grain)


class _EditionHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.kind: EditionKind | None = None
        self.period_code = ""
        self.empty_next_action: str | None = None
        self.sections: list[dict[str, object]] = []
        self._section: dict[str, object] | None = None
        self._capture: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = {key: value or "" for key, value in attrs}
        if tag == "article":
            kind = found.get("data-kind")
            if kind in {"week", "month"}:
                self.kind = kind
            self.period_code = found.get("data-period", "")
        elif tag == "section":
            grain = found.get("data-grain", "corporate")
            if grain not in GRAIN_SECTION_LABEL:
                grain = "corporate"
            self._section = {
                "grain_code": grain,
                "unit_id": "",
                "unit_label": "",
                "titles": [],
                "empty_next_action": None,
            }
        elif tag == "h2":
            self._capture = "heading"
            self._text = []
        elif tag == "li":
            self._capture = "title"
            self._text = []
        elif tag == "p" and found.get("class") == "newspaper-empty":
            self._capture = "empty"
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        text = "".join(self._text).strip()
        if tag == "h2" and self._section is not None and self._capture == "heading":
            if " · " in text:
                self._section["unit_label"] = text.split(" · ", 1)[1]
        elif tag == "li" and self._section is not None and self._capture == "title":
            titles = self._section["titles"]
            if isinstance(titles, list):
                titles.append(text)
        elif tag == "p" and self._capture == "empty":
            if self._section is not None:
                self._section["empty_next_action"] = text
            else:
                self.empty_next_action = text
        elif tag == "section" and self._section is not None:
            self.sections.append(self._section)
            self._section = None
        self._capture = None
        self._text = []


def edition_from_row(
    thread_group_key: str,
    secondary_grouping_key: str,
    post_body: str,
) -> dict[str, object] | None:
    """Structured edition for the board list, or None when not a newspaper."""
    if not is_newspaper_thread(thread_group_key):
        return None
    parser = _EditionHtmlParser()
    parser.feed(post_body)
    kind: EditionKind = parser.kind or ("week" if thread_group_key == newspaper_thread_key("week") else "month")
    has_titles = any(
        isinstance(section.get("titles"), list) and section["titles"] for section in parser.sections
    )
    return {
        "kind": kind,
        "period_code": parser.period_code or secondary_grouping_key,
        "sections": parser.sections,
        "empty_next_action": None if has_titles else parser.empty_next_action,
    }
