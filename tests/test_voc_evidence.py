"""Extractive VOC evidence quotes the sentence that names the org."""

from __future__ import annotations

from lineageweave.fixtures import (
    fixture_thread_cast,
    homonym_person_catalog_rows,
    sample_records,
)
from lineageweave.voc_evidence import first_excerpt_for, sentence_excerpts

_BODY = (
    "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid "
    "about the delayed shipment. The weather in Gwangju was irrelevant."
)


def test_only_sentences_that_name_an_organization_are_kept() -> None:
    excerpts = sentence_excerpts(_BODY, ("Northridge Grid", "Demo Corp"))
    assert excerpts == (
        "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid "
        "about the delayed shipment.",
    )


def test_unmentioned_organization_yields_no_excerpt() -> None:
    assert sentence_excerpts(_BODY, ("Totally Different Company",)) == ()
    assert first_excerpt_for(_BODY, "Totally Different Company") is None


def test_matching_is_case_insensitive() -> None:
    excerpts = sentence_excerpts(_BODY, ("demo corp",))
    assert "Demo Corp" in excerpts[0]


def test_empty_inputs_are_missing_evidence_not_a_guess() -> None:
    assert sentence_excerpts("", ("Demo Corp",)) == ()
    assert sentence_excerpts(_BODY, ()) == ()
    assert sentence_excerpts(_BODY, ("  ",)) == ()
    assert first_excerpt_for(_BODY, "") is None


def test_first_excerpt_returns_the_matching_sentence() -> None:
    assert first_excerpt_for(_BODY, "Northridge Grid") == (
        "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid "
        "about the delayed shipment."
    )


def test_proj_alpha_cast_names_northridge_and_uncast_stays_empty() -> None:
    """Event Lineage click-through must have extractable VOC evidence."""
    fork = fixture_thread_cast("Pricing renegotiation follow-up")
    assert fork is not None
    assert fork.organization_name == "Northridge Grid"
    assert "Ada West" in fork.person_names
    assert fork.body is not None
    assert sentence_excerpts(fork.body, (fork.organization_name,))
    assert fixture_thread_cast("Unrelated: annual account review") is None
    spec = fixture_thread_cast("Technical specification review meeting")
    assert spec is not None
    assert spec.organization_name == "Westfield Power"
    assert "Jordan Hale" in spec.person_names
    assert spec.body is not None
    assert sentence_excerpts(spec.body, (spec.organization_name,))
    calendar = fixture_thread_cast("Follow-up on the Riverbend order confirmation")
    assert calendar is not None
    assert calendar.organization_name == "Riverbend"
    assert not calendar.person_names
    alpha = [rec.label for rec in sample_records() if rec.secondary_key == "proj-alpha"]
    assert len(alpha) == 5
    assert all(fixture_thread_cast(title) is not None for title in alpha)


def test_homonym_person_catalog_rows_share_a_name_and_order_by_created_at() -> None:
    """Two catalog people can share a display name; the earlier row is first."""

    earlier, later = homonym_person_catalog_rows()
    assert earlier.person_name == later.person_name
    assert earlier.person_name == "Kim Cheolsu"
    assert earlier.created_at < later.created_at
    assert earlier.person_side_code == "our_side"
    assert later.person_side_code == "counterparty"
    assert earlier.last_known_job_title != later.last_known_job_title
