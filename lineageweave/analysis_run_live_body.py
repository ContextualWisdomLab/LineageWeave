"""Compare a live ``source_post`` write clock with an analysis-run cutoff.

The registry lists titles by ``created_at <= knowledge_cutoff`` (ADR 0016).
That inclusion clock is not the live row's write clock. A later rewrite
of an in-cutoff title must not be treated as reconstructed evidence.

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).
"""

from __future__ import annotations

from datetime import datetime


def live_body_written_after_cutoff(
    knowledge_cutoff: datetime,
    updated_at: datetime,
) -> bool:
    """Return True when the live row was written after the analysis clock.

    Both arguments must be timezone-aware instants. A write exactly at
    the cutoff stays inside the run (the same ``<=`` gate as title
    inclusion).
    """
    return updated_at > knowledge_cutoff
