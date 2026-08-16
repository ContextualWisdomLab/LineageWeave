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
A tied top score therefore stays unbound (ADR 0021; Fellegi & Sunter,
1969) instead of first-winning a homonym.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

DEFAULT_MIN_SIMILARITY = 0.6

# Legal-entity suffixes stripped before comparison so "Acme Electronics
# Korea Ltd." and "Acme Electronics Korea" don't get penalized for a
# difference that carries no identifying information.
_CORPORATE_SUFFIXES = ("inc", "llc", "corp", "co", "ltd", "gmbh", "plc", "kk")
_SUFFIX_PATTERN = re.compile(r"\b(?:" + "|".join(_CORPORATE_SUFFIXES) + r")\b")
_PUNCTUATION_PATTERN = re.compile(r"[.,]")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_organization_name(name: str) -> str:
    """Lowercases, strips punctuation and common legal-entity suffixes, and
    collapses whitespace -- the normalization both sides of a similarity
    comparison go through.
    """
    lowered = _PUNCTUATION_PATTERN.sub("", name.strip().lower())
    lowered = _SUFFIX_PATTERN.sub("", lowered)
    return _WHITESPACE_PATTERN.sub(" ", lowered).strip()


@dataclass(frozen=True)
class CorporateEntityCandidate:
    """One existing `corporate_entity` row eligible to resolve against."""

    corporate_entity_id: str
    entity_name: str


def resolve_corporate_entity(
    mentioned_name: str,
    candidates: Sequence[CorporateEntityCandidate],
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> str | None:
    """Return the unique best-matching catalog id, or ``None``.

    ``None`` is the honest outcome when no candidate clears
    ``min_similarity`` **or** two or more candidates share the top
    score. A wrong hierarchy link corrupts every downstream Knowledge
    Graph walk, so a tied homonym must not become a button (ADR 0021;
    Fellegi & Sunter, 1969; Bhattacharya & Getoor, 2007). Duplicate
    rows for the same ``corporate_entity_id`` still count as one
    candidate.
    """
    normalized_mention = normalize_organization_name(mentioned_name)
    if not normalized_mention:
        return None

    best_ids: list[str] = []
    best_score = 0.0
    for candidate in candidates:
        score = SequenceMatcher(
            None, normalized_mention, normalize_organization_name(candidate.entity_name)
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

    if best_score < min_similarity or len(best_ids) != 1:
        return None
    return best_ids[0]
