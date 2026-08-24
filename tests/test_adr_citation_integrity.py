"""Regression guard against a specific fabricated APA citation.

ADR 0024 previously attributed the RankWeave temporal/lexical channel
weight to a paper -- "Samuel, D., MacAvaney, S., Yates, A., Zhang, E.,
Zhang, S., Macdonald, C., & Ounis, I. (2025). Weighted reciprocal rank
fusion for multi-channel retrieval [Preprint]" -- that does not exist.
It combined real information-retrieval researchers' names into a title
no search or bibliography lookup could confirm. This test does not
re-verify citations against the live web (that is the job of the
citation-integrity sweep, not CI); it only pins the specific correction
so the fabricated string cannot silently reappear via a careless revert
or copy-paste from an older draft.
"""

from __future__ import annotations

from pathlib import Path


def test_rankweave_adr_no_longer_cites_the_fabricated_paper() -> None:
    adr = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "adr"
        / "0024-rankweave-fusion-fail-closed.md"
    ).read_text(encoding="utf-8")

    assert "Correction (2026-08-24)" in adr

    references_section = adr.split("## References", 1)[1]
    assert "Samuel, D." not in references_section
    assert "Weighted reciprocal rank fusion for multi-channel retrieval" not in references_section
    assert "Efron, M., & Golovchinsky, G. (2011)" in references_section

    decision_section = adr.split("## Decision", 1)[1].split("## Consequences", 1)[0]
    assert "Samuel et al." not in decision_section
