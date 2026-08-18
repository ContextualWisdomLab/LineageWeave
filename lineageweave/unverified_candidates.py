"""Searxng hits stay 미검증 후보 until attached on 고객 마스터.

Candidates appear only in Ask Agent / grounded Q&A. They are never
drawn as Event Lineage parents. Promote sends the buyer to 고객
마스터. Attach unique-matches an existing catalog row and never
creates an AUTO- row from a search hit (ADR 0026).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from .corporate_hierarchy_resolution import (
    RESOLUTION_TIE,
    RESOLUTION_UNIQUE,
    CorporateEntityCandidate,
    score_corporate_entity,
)
from .relation_verification import corroborating_evidence_url

UNVERIFIED_CANDIDATE_LABEL = "미검증 후보"
PROMOTE_DESTINATION = "customers"
ATTACH_UNIQUE_NEXT_ACTION = None
ATTACH_TIE_NEXT_ACTION = "그 객체는 온톨로지에 아직 없습니다"
ATTACH_MISS_NEXT_ACTION = "그 객체는 온톨로지에 아직 없습니다"

_TRAILING_PUNCT = re.compile(r"[?.!\s]+$")
_OUTSIDE_TOKENS = (
    "실제",
    "외부",
    "부모",
    "parent",
    "outside",
    "확인",
    "온톨로지 없",
    "미검증",
)


@dataclass(frozen=True)
class UnverifiedCandidate:
    """One Searxng hit that is not lineage truth."""

    label: str
    evidence_url: str | None
    status_label: str = UNVERIFIED_CANDIDATE_LABEL
    promote_destination: str = PROMOTE_DESTINATION


@dataclass(frozen=True)
class OntologyAttachResult:
    """Unique catalog bind, or fail-closed. Never an invented AUTO- row."""

    attached: bool
    catalog_id: str | None
    empty_next_action: str | None


def wants_outside_verification(question: str) -> bool:
    """True when Ask Agent should check a 5W1H / lineage inference outside."""
    folded = _TRAILING_PUNCT.sub("", " ".join(question.strip().lower().split()))
    return any(token in folded for token in _OUTSIDE_TOKENS)


def candidates_from_search_results(
    organization_name: str,
    results: Sequence[dict[str, Any]],
) -> tuple[UnverifiedCandidate, ...]:
    """Label hits as 미검증 후보. Do not mark them as lineage parents."""
    out: list[UnverifiedCandidate] = []
    seen: set[str] = set()
    for result in results:
        if not isinstance(result, dict):
            continue
        title = str(result.get("title") or "").strip()
        url = corroborating_evidence_url(organization_name, result)
        if not title or title in seen:
            continue
        seen.add(title)
        out.append(UnverifiedCandidate(label=title, evidence_url=url))
    return tuple(out)


def stub_unverified_candidate(organization_name: str) -> tuple[UnverifiedCandidate, ...]:
    """Label an opened-post org as 미검증 후보. No live web search."""
    label = organization_name.strip()
    if not label:
        return ()
    return (UnverifiedCandidate(label=label, evidence_url=None),)


def attach_unverified_candidate(
    organization_name: str,
    candidates: Sequence[CorporateEntityCandidate],
) -> OntologyAttachResult:
    """Bind only a unique existing catalog row. Tie and miss stay unbound."""
    resolution = score_corporate_entity(organization_name, candidates)
    if resolution.kind == RESOLUTION_UNIQUE:
        return OntologyAttachResult(
            attached=True,
            catalog_id=resolution.catalog_id,
            empty_next_action=ATTACH_UNIQUE_NEXT_ACTION,
        )
    if resolution.kind == RESOLUTION_TIE:
        return OntologyAttachResult(
            attached=False,
            catalog_id=None,
            empty_next_action=ATTACH_TIE_NEXT_ACTION,
        )
    return OntologyAttachResult(
        attached=False,
        catalog_id=None,
        empty_next_action=ATTACH_MISS_NEXT_ACTION,
    )


def candidate_payloads(candidates: Sequence[UnverifiedCandidate]) -> list[dict[str, object]]:
    """Buyer JSON for Ask Agent. Status stays 미검증 후보."""
    return [
        {
            "label": row.label,
            "evidence_url": row.evidence_url,
            "status_label": row.status_label,
            "promote_destination": row.promote_destination,
        }
        for row in candidates
    ]


__all__ = [
    "ATTACH_MISS_NEXT_ACTION",
    "ATTACH_TIE_NEXT_ACTION",
    "OntologyAttachResult",
    "PROMOTE_DESTINATION",
    "UNVERIFIED_CANDIDATE_LABEL",
    "UnverifiedCandidate",
    "attach_unverified_candidate",
    "candidate_payloads",
    "candidates_from_search_results",
    "stub_unverified_candidate",
    "wants_outside_verification",
]
