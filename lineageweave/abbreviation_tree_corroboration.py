"""Cross-check a post abbreviation against the customer-group tree.

ADR 0008 asks an LLM to invent a canonical name, then Searxng-verifies
that pairing. This module does not invent a name and does not create a
``corporate_entity`` row. It only asks the existing Searxng client
whether a raw mention corroborates against a node already on the
authorized tree.

Fail-closed (Thorne, Vlachos, Christodoulopoulos, & Mittal, 2018;
Fellegi & Sunter, 1969):

- Searxng unavailable or a search that raises: no parent, no AUTO row.
- Zero corroborated nodes: unbound.
- Two or more corroborated nodes: unbound (a tie is not a first-win).
- Exactly one corroborated node: bind that catalog id.

A mention that already uniquely equals a catalog name is not an
abbreviation -- callers skip it so Searxng is reserved for the
altLabel case (Miles & Bechhofer, 2009).
"""

from __future__ import annotations

from dataclasses import dataclass

from .corporate_hierarchy_resolution import normalize_organization_name
from .relation_verification import (
    STATUS_CORROBORATED,
    STATUS_PENDING,
    STATUS_UNCORROBORATED,
    RelationVerificationClient,
    RelationVerificationResult,
)


@dataclass(frozen=True)
class TreeEntityCandidate:
    """One authorized catalog node Searxng may corroborate against."""

    entity_id: str
    entity_name: str


@dataclass(frozen=True)
class AbbreviationTreeMatch:
    """One raw mention's tree-constrained Searxng outcome.

    Attributes:
        raw_organization_name: the mention as written on the post.
        corporate_entity_id: the unique corroborated catalog id, or
            ``None`` when the channel is pending, empty, or tied.
        verification_status_code: ``relation_verification_status`` code.
        verification_evidence_url: the unique hit's evidence URL, or
            ``None`` when unbound.
    """

    raw_organization_name: str
    corporate_entity_id: str | None
    verification_status_code: str
    verification_evidence_url: str | None


def exact_catalog_matches(
    raw_name: str,
    candidates: tuple[TreeEntityCandidate, ...] | list[TreeEntityCandidate],
) -> tuple[TreeEntityCandidate, ...]:
    """Catalog nodes whose normalized name equals the raw mention."""
    normalized = normalize_organization_name(raw_name)
    if not normalized:
        return ()
    return tuple(
        candidate
        for candidate in candidates
        if normalize_organization_name(candidate.entity_name) == normalized
    )


def abbreviation_candidates(
    raw_names: tuple[str, ...] | list[str],
    tree_nodes: tuple[TreeEntityCandidate, ...] | list[TreeEntityCandidate],
) -> tuple[str, ...]:
    """Mentions that are not already a unique catalog name.

    Empty strings are dropped. A unique exact catalog match is already
    bound by identity and is not sent to Searxng. A tied exact match
    stays in the list so Searxng can still fail closed rather than
    first-winning a homonym.
    """
    seen: set[str] = set()
    kept: list[str] = []
    for raw_name in raw_names:
        stripped = raw_name.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        matches = exact_catalog_matches(stripped, tree_nodes)
        if len(matches) == 1:
            continue
        kept.append(stripped)
    return tuple(kept)


def corroborate_abbreviation_against_tree(
    raw_name: str,
    candidates: tuple[TreeEntityCandidate, ...] | list[TreeEntityCandidate],
    verification_client: RelationVerificationClient,
) -> AbbreviationTreeMatch:
    """Bind ``raw_name`` to a unique tree node, or leave it unbound.

    A failed search must raise -- that is not
    ``STATUS_UNCORROBORATED``. An unavailable client returns
    ``STATUS_PENDING`` with no catalog id.
    """
    stripped = raw_name.strip()
    if not stripped:
        return AbbreviationTreeMatch(
            raw_organization_name=raw_name,
            corporate_entity_id=None,
            verification_status_code=STATUS_UNCORROBORATED,
            verification_evidence_url=None,
        )
    if not verification_client.available:
        return AbbreviationTreeMatch(
            raw_organization_name=stripped,
            corporate_entity_id=None,
            verification_status_code=STATUS_PENDING,
            verification_evidence_url=None,
        )

    corroborated: list[tuple[TreeEntityCandidate, RelationVerificationResult]] = []
    for candidate in candidates:
        result = verification_client.verify(candidate.entity_name, stripped)
        if result.status_code == STATUS_CORROBORATED:
            corroborated.append((candidate, result))

    if len(corroborated) == 1:
        candidate, result = corroborated[0]
        return AbbreviationTreeMatch(
            raw_organization_name=stripped,
            corporate_entity_id=candidate.entity_id,
            verification_status_code=STATUS_CORROBORATED,
            verification_evidence_url=result.evidence_url,
        )
    return AbbreviationTreeMatch(
        raw_organization_name=stripped,
        corporate_entity_id=None,
        verification_status_code=STATUS_UNCORROBORATED,
        verification_evidence_url=None,
    )
