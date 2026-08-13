"""Extractive VOC evidence quotes the sentence that names the org."""

from __future__ import annotations

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
