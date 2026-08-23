"""Resolves a free-text organization name mentioned in a post to an
existing `corporate_entity` row, even when the string doesn't match
exactly -- an abbreviation ("Acme Elec Korea"), a trailing legal suffix
("Acme Electronics Korea Ltd."), or a subsidiary's own trading name should
still resolve to the same entity a human would recognize.

Grounded in Bhattacharya & Getoor (2007): collective entity resolution
argues that ambiguous references are best resolved using relational
context (which other entities/records co-occur with this one), not string
similarity in isolation. This module implements the practical first stage
most collective-ER pipelines still need -- candidate generation and
similarity-based scoring against known entities -- documented honestly as
that stage, not the full joint/collective inference: a genuinely collective
resolver would also weigh which OTHER organizations and people are
co-mentioned in the same post against the target entity's own known
affiliates, and could resolve two *different* ambiguous mentions in the
same post jointly rather than independently. That joint step is a real
upgrade path once real usage shows single-mention similarity scoring
under- or over-resolving in practice -- it is not implemented here because
nothing yet demonstrates the need for it over this simpler, cheaper stage.
A tied top score therefore stays unbound (ADR 0026; Fellegi & Sunter,
1969) instead of first-winning a homonym.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

DEFAULT_MIN_SIMILARITY = 0.6
RESOLUTION_UNIQUE = "unique"
RESOLUTION_MISS = "miss"
RESOLUTION_TIE = "tie"
CorporateEntityResolutionKind = Literal["unique", "miss", "tie"]

# Legal-entity suffixes stripped before comparison so "Acme Electronics
# Korea Ltd." and "Acme Electronics Korea" don't get penalized for a
# difference that carries no identifying information.
_CORPORATE_SUFFIXES = ("inc", "llc", "corp", "co", "ltd", "gmbh", "plc", "kk")
_SUFFIX_PATTERN = re.compile(r"\b(?:" + "|".join(_CORPORATE_SUFFIXES) + r")\b")
_PUNCTUATION_PATTERN = re.compile(r"[.,]")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_organization_name(name: str) -> str:
    """Lowercase and normalize one organization name for comparison."""
    lowered = _PUNCTUATION_PATTERN.sub("", name.strip().lower())
    lowered = _SUFFIX_PATTERN.sub("", lowered)
    return _WHITESPACE_PATTERN.sub(" ", lowered).strip()


@dataclass(frozen=True)
class CorporateEntityCandidate:
    """One existing `corporate_entity` row eligible to resolve against."""

    corporate_entity_id: str
    entity_name: str


@dataclass(frozen=True)
class OrganizationNameAlias:
    """One corroborated SKOS alt/pref pair for the same organization.

    ``alt_label`` is the abbreviated/slang form stored as
    ``organization_name_resolution.raw_organization_name``. ``pref_label``
    is the canonical form stored as ``resolved_organization_name``. Only
    search-corroborated rows belong here (ADR 0008 / ADR 0120).
    """

    alt_label: str
    pref_label: str


@dataclass(frozen=True)
class CorporateEntityResolution:
    """Candidate-generation outcome for one mentioned organization name.

    ``None`` from :func:`resolve_corporate_entity` used to mean both
    "no catalog row is close enough" and "two catalog rows tied."
    Those are different decisions. A miss may enter ADR 0010 creation.
    A tie must not invent a third same-named row (ADR 0026; Fellegi &
    Sunter, 1969).

    Attributes:
        kind: ``unique`` stores ``catalog_id``. ``miss`` means no
            candidate cleared ``min_similarity``. ``tie`` means two
            or more distinct catalog ids share the top score at or
            above the threshold.
        catalog_id: The unique winner, or ``None``.
        top_score: Highest similarity seen, or ``0.0`` when the
            mention is empty.
        top_catalog_ids: Distinct catalog ids that share
            ``top_score``. Empty on a miss that never scored.
    """

    kind: CorporateEntityResolutionKind
    catalog_id: str | None
    top_score: float
    top_catalog_ids: tuple[str, ...]


def score_corporate_entity(
    mentioned_name: str,
    candidates: Sequence[CorporateEntityCandidate],
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> CorporateEntityResolution:
    """Classify a mention as a unique match, a miss, or a tied match.

    Duplicate snapshot rows for the same ``corporate_entity_id`` count
    as one candidate. Only a unique top score may bind; a tie stays
    unbound, while a genuine miss may enter the separately corroborated
    creation path defined by ADR 0010.
    """
    normalized_mention = normalize_organization_name(mentioned_name)
    if not normalized_mention:
        return CorporateEntityResolution(
            kind=RESOLUTION_MISS,
            catalog_id=None,
            top_score=0.0,
            top_catalog_ids=(),
        )

    best_ids: list[str] = []
    best_score = 0.0
    for candidate in candidates:
        score = SequenceMatcher(
            None,
            normalized_mention,
            normalize_organization_name(candidate.entity_name),
        ).ratio()
        if score > best_score:
            best_score = score
            best_ids = [candidate.corporate_entity_id]
        elif (
            score == best_score
            and score > 0.0
            and candidate.corporate_entity_id not in best_ids
        ):
            best_ids.append(candidate.corporate_entity_id)

    if best_score < min_similarity or not best_ids:
        return CorporateEntityResolution(
            kind=RESOLUTION_MISS,
            catalog_id=None,
            top_score=best_score,
            top_catalog_ids=tuple(best_ids),
        )
    if len(best_ids) != 1:
        return CorporateEntityResolution(
            kind=RESOLUTION_TIE,
            catalog_id=None,
            top_score=best_score,
            top_catalog_ids=tuple(best_ids),
        )
    return CorporateEntityResolution(
        kind=RESOLUTION_UNIQUE,
        catalog_id=best_ids[0],
        top_score=best_score,
        top_catalog_ids=tuple(best_ids),
    )


def resolve_corporate_entity(
    mentioned_name: str,
    candidates: Sequence[CorporateEntityCandidate],
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> str | None:
    """Return the unique best-matching catalog id, or ``None``.

    ``None`` is the fail-closed outcome when no candidate clears
    ``min_similarity`` or when distinct candidates share the top score.
    Callers that may create a row must use :func:`score_corporate_entity`
    to distinguish a miss from a tie (ADR 0026).
    """
    return score_corporate_entity(
        mentioned_name,
        candidates,
        min_similarity,
    ).catalog_id


def expand_candidates_with_skos_aliases(
    candidates: Sequence[CorporateEntityCandidate],
    aliases: Sequence[OrganizationNameAlias],
) -> list[CorporateEntityCandidate]:
    """Expose each corroborated SKOS pair as another label on the same row.

    Catalog matching is still string similarity (Bhattacharya & Getoor,
    2007 candidate generation). An initialism shares almost no substring
    with its expansion, so a corroborated ``skos:altLabel`` /
    ``skos:prefLabel`` pair (Miles & Bechhofer, 2009) is projected onto
    the catalog id that already holds either label. Duplicate labels for
    the same id stay one candidate. A later ``score_corporate_entity``
    call still fail-closes on a tie.

    Uncorroborated pairs must not be supplied. Empty or identical labels
    are ignored so a no-op resolution cannot manufacture a match.
    """
    expanded = list(candidates)
    seen = {
        (candidate.corporate_entity_id, normalize_organization_name(candidate.entity_name))
        for candidate in candidates
        if normalize_organization_name(candidate.entity_name)
    }
    for candidate in candidates:
        catalog_key = normalize_organization_name(candidate.entity_name)
        if not catalog_key:
            continue
        for alias in aliases:
            alt_key = normalize_organization_name(alias.alt_label)
            pref_key = normalize_organization_name(alias.pref_label)
            if not alt_key or not pref_key or alt_key == pref_key:
                continue
            extra_name: str | None = None
            if catalog_key == pref_key:
                extra_name = alias.alt_label
            elif catalog_key == alt_key:
                extra_name = alias.pref_label
            if extra_name is None:
                continue
            extra_key = (
                candidate.corporate_entity_id,
                normalize_organization_name(extra_name),
            )
            if extra_key in seen:
                continue
            seen.add(extra_key)
            expanded.append(
                CorporateEntityCandidate(
                    corporate_entity_id=candidate.corporate_entity_id,
                    entity_name=extra_name,
                )
            )
    return expanded
