"""Extractive VOC evidence: the sentences that actually name an org.

A post's ``voc_type_code`` is a governed Voice-of-X lookup (ADR 0246).
The operator-visible evidence for that label is not a second LLM guess --
it is the span in the post that mentions a classified counterparty or a
Keyman's affiliated organization (ACE mention extent; Doddington et al.,
2004). A name that never appears yields no excerpt:
a missing mention is not a fabricated quote.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def sentence_excerpts(
    source_text: str, organization_names: Sequence[str]
) -> tuple[str, ...]:
    """Return sentences in ``source_text`` that mention an organization.

    Matching is case-insensitive and substring-based on the stored
    organization string. Empty text, empty names, or no hits return
    ``()`` -- never a guessed sentence.
    """
    normalized_organization_names = [
        organization_name.strip()
        for organization_name in organization_names
        if isinstance(organization_name, str) and organization_name.strip()
    ]
    if not source_text or not normalized_organization_names:
        return ()
    evidence_excerpts: list[str] = []
    seen_excerpt_texts: set[str] = set()
    for excerpt_sentence in _SENTENCE_SPLIT.split(source_text.strip()):
        excerpt_sentence = excerpt_sentence.strip()
        if not excerpt_sentence:
            continue
        lowercase_sentence = excerpt_sentence.lower()
        if (
            any(
                organization_name.lower() in lowercase_sentence
                for organization_name in normalized_organization_names
            )
            and excerpt_sentence not in seen_excerpt_texts
        ):
            seen_excerpt_texts.add(excerpt_sentence)
            evidence_excerpts.append(excerpt_sentence)
    return tuple(evidence_excerpts)


def first_excerpt_for(source_text: str, organization_name: str) -> str | None:
    """The first sentence that names this organization, or ``None``."""
    organization_excerpts = sentence_excerpts(source_text, (organization_name,))
    return organization_excerpts[0] if organization_excerpts else None
