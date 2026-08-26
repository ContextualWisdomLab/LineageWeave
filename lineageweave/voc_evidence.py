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


def sentence_excerpts(text: str, organization_names: Sequence[str]) -> tuple[str, ...]:
    """Return the sentences in ``text`` that mention at least one name.

    Matching is case-insensitive and substring-based on the stored
    organization string. Empty text, empty names, or no hits return
    ``()`` -- never a guessed sentence.
    """
    names = [name.strip() for name in organization_names if isinstance(name, str) and name.strip()]
    if not text or not names:
        return ()
    excerpts: list[str] = []
    seen: set[str] = set()
    for sentence in _SENTENCE_SPLIT.split(text.strip()):
        sentence = sentence.strip()
        if not sentence:
            continue
        lowered = sentence.lower()
        if any(name.lower() in lowered for name in names) and sentence not in seen:
            seen.add(sentence)
            excerpts.append(sentence)
    return tuple(excerpts)


def first_excerpt_for(text: str, organization_name: str) -> str | None:
    """The first sentence that names this organization, or ``None``."""
    excerpts = sentence_excerpts(text, (organization_name,))
    return excerpts[0] if excerpts else None
