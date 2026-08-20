"""RED contracts for the Buyer project-history timeline."""

from __future__ import annotations

import pytest

from lineageweave.project_history import (
    classify_project_event,
    normalize_project_key,
    responsibility_transition_code,
)


def test_project_identity_is_exact_but_unicode_compatible() -> None:
    """Compatibility forms may normalize; fuzzy project binding may not."""
    assert normalize_project_key("  Ｐ－１００  ") == "p-100"
    assert normalize_project_key("P-100-A") != normalize_project_key("P-100")
    with pytest.raises(ValueError):
        normalize_project_key("   ")


def test_event_display_classification_does_not_create_authority() -> None:
    """The lifecycle label is presentation metadata over an existing post."""
    assert (
        classify_project_event(
            title="Contract awarded",
            source_stage_code=None,
            source_detail_state_code=None,
            voc_type_code=None,
            is_focus=False,
        )
        == "contract_awarded"
    )
    for is_focus in (False, True):
        assert (
            classify_project_event(
                title="Field complaint received",
                source_stage_code=None,
                source_detail_state_code=None,
                voc_type_code="voc",
                is_focus=is_focus,
            )
            == "voc_received"
        )


def test_responsibility_transition_describes_document_evidence_only() -> None:
    """Missing adjacent evidence is a visible evidence gap, not an HR fact."""
    assert responsibility_transition_code(["person:a"], ["person:a"]) == "continuous"
    assert responsibility_transition_code(["person:a"], ["person:b"]) == "handoff"
    assert responsibility_transition_code(["person:a"], []) == "assignment_gap"
