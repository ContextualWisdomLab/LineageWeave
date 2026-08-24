"""Regression guard against specific citation-integrity bugs an ADR-wide
sweep found and fixed.

- ADR 0024 previously attributed the RankWeave temporal/lexical channel
  weight to a paper -- "Samuel, D., MacAvaney, S., Yates, A., Zhang, E.,
  Zhang, S., Macdonald, C., & Ounis, I. (2025). Weighted reciprocal rank
  fusion for multi-channel retrieval [Preprint]" -- that does not exist.
  It combined real information-retrieval researchers' names into a title
  no search or bibliography lookup could confirm.
- ADR 0025 and ADR 0137 both cited the real W3C PROV-O document (correct
  title and URL) but attributed it to "Moreau, L., & Missier, P. (Eds.)."
  Those are the real editors of the sibling same-day PROV-DM spec, not
  PROV-O -- PROV-O's real editors are Lebo, Sahoo, & McGuinness (2013).

These tests do not re-verify citations against the live web (that is the
job of the citation-integrity sweep, not CI); they only pin the specific
corrections so the errors cannot silently reappear via a careless revert
or copy-paste from an older draft.
"""

from __future__ import annotations

from pathlib import Path

_ADR_DIR = Path(__file__).resolve().parents[1] / "docs" / "adr"


def test_rankweave_adr_no_longer_cites_the_fabricated_paper() -> None:
    adr = (_ADR_DIR / "0024-rankweave-fusion-fail-closed.md").read_text(encoding="utf-8")

    assert "Correction (2026-08-24)" in adr

    references_section = adr.split("## References", 1)[1]
    assert "Samuel, D." not in references_section
    assert "Weighted reciprocal rank fusion for multi-channel retrieval" not in references_section
    assert "Efron, M., & Golovchinsky, G. (2011)" in references_section

    decision_section = adr.split("## Decision", 1)[1].split("## Consequences", 1)[0]
    assert "Samuel et al." not in decision_section


def test_source_post_revision_adr_attributes_prov_o_to_its_real_editors() -> None:
    adr = (_ADR_DIR / "0025-source-post-revision.md").read_text(encoding="utf-8")

    assert "Correction (2026-08-24)" in adr
    assert "Lebo et al., 2013" in adr

    context_section = adr.split("## Context", 1)[1].split("## Decision", 1)[0]
    assert "Moreau & Missier, 2013" not in context_section

    references_section = adr.split("## References", 1)[1]
    assert "Moreau, L., & Missier, P." not in references_section
    assert "Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013)" in references_section


def test_cross_post_customer_identity_adr_attributes_prov_o_to_its_real_editors() -> None:
    adr = (_ADR_DIR / "0137-cross-post-customer-identity.md").read_text(encoding="utf-8")

    assert "Correction (2026-08-24)" in adr

    references_section = adr.split("## References (APA 7th)", 1)[1]
    assert "Moreau, L., & Missier, P." not in references_section
    assert "Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013)" in references_section
