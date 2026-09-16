"""Extractive VOC evidence quotes the sentence that names the org."""

from __future__ import annotations

import ast
from pathlib import Path

from lineageweave.fixtures import fixture_thread_cast, sample_records
from lineageweave.voc_evidence import first_excerpt_for, sentence_excerpts

VOC_EVIDENCE_SOURCE_PATH = (
    Path(__file__).parents[1] / "lineageweave" / "voc_evidence.py"
)
AFFILIATE_INGESTION_SOURCE_PATH = (
    Path(__file__).parents[1] / "backend" / "app" / "affiliate_tree_ingestion.py"
)
FORBIDDEN_VOC_EVIDENCE_IDENTIFIERS = {
    "aliases",
    "codes",
    "conn",
    "counterparties",
    "entities",
    "excerpts",
    "forest",
    "leaves",
    "level",
    "lowered",
    "name",
    "names",
    "node",
    "nodes",
    "person",
    "row",
    "seen",
    "sentence",
    "side",
    "text",
}

_SOURCE_BODY = (
    "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid "
    "about the delayed shipment. The weather in Gwangju was irrelevant."
)


def test_voc_evidence_uses_extract_and_affiliate_specific_identifiers() -> None:
    """Keep owned identifiers aligned with the extractive VOC evidence domain."""
    owned_identifiers: set[str] = set()
    for source_path in (VOC_EVIDENCE_SOURCE_PATH, AFFILIATE_INGESTION_SOURCE_PATH):
        source_tree = ast.parse(source_path.read_text(encoding="utf-8"))
        owned_identifiers.update(
            syntax_node.id
            for syntax_node in ast.walk(source_tree)
            if isinstance(syntax_node, ast.Name)
        )
        owned_identifiers.update(
            syntax_node.arg
            for syntax_node in ast.walk(source_tree)
            if isinstance(syntax_node, ast.arg)
        )

    assert not (FORBIDDEN_VOC_EVIDENCE_IDENTIFIERS & owned_identifiers)
    assert {
        "affiliate_forest",
        "affiliate_node",
        "counterparty_row",
        "database_connection",
        "evidence_excerpts",
        "evidence_organization_names",
        "excerpt_sentence",
        "normalized_organization_names",
        "source_text",
    } <= owned_identifiers


def test_only_sentences_that_name_an_organization_are_kept() -> None:
    matching_excerpts = sentence_excerpts(
        _SOURCE_BODY, ("Northridge Grid", "Demo Corp")
    )
    assert matching_excerpts == (
        "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid "
        "about the delayed shipment.",
    )


def test_unmentioned_organization_yields_no_excerpt() -> None:
    assert sentence_excerpts(_SOURCE_BODY, ("Totally Different Company",)) == ()
    assert first_excerpt_for(_SOURCE_BODY, "Totally Different Company") is None


def test_matching_is_case_insensitive() -> None:
    matching_excerpts = sentence_excerpts(_SOURCE_BODY, ("demo corp",))
    assert "Demo Corp" in matching_excerpts[0]


def test_empty_inputs_are_missing_evidence_not_a_guess() -> None:
    assert sentence_excerpts("", ("Demo Corp",)) == ()
    assert sentence_excerpts(_SOURCE_BODY, ()) == ()
    assert sentence_excerpts(_SOURCE_BODY, ("  ",)) == ()
    assert first_excerpt_for(_SOURCE_BODY, "") is None


def test_first_excerpt_returns_the_matching_sentence() -> None:
    assert first_excerpt_for(_SOURCE_BODY, "Northridge Grid") == (
        "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid "
        "about the delayed shipment."
    )


def test_proj_alpha_cast_names_northridge_and_uncast_stays_empty() -> None:
    """Event Lineage click-through must have extractable VOC evidence."""
    pricing_thread_cast = fixture_thread_cast("Pricing renegotiation follow-up")
    assert pricing_thread_cast is not None
    assert pricing_thread_cast.organization_name == "Northridge Grid"
    assert "Ada West" in pricing_thread_cast.person_names
    assert pricing_thread_cast.body is not None
    assert sentence_excerpts(
        pricing_thread_cast.body, (pricing_thread_cast.organization_name,)
    )
    assert fixture_thread_cast("Unrelated: annual account review") is None
    specification_thread_cast = fixture_thread_cast(
        "Technical specification review meeting"
    )
    assert specification_thread_cast is not None
    assert specification_thread_cast.organization_name == "Westfield Power"
    assert "Jordan Hale" in specification_thread_cast.person_names
    assert specification_thread_cast.body is not None
    assert sentence_excerpts(
        specification_thread_cast.body,
        (specification_thread_cast.organization_name,),
    )
    calendar_thread_cast = fixture_thread_cast(
        "Follow-up on the Riverbend order confirmation"
    )
    assert calendar_thread_cast is not None
    assert calendar_thread_cast.organization_name == "Riverbend"
    assert not calendar_thread_cast.person_names
    project_alpha_labels = [
        lineage_record.label
        for lineage_record in sample_records()
        if lineage_record.secondary_key == "proj-alpha"
    ]
    assert len(project_alpha_labels) == 5
    assert all(
        fixture_thread_cast(record_title) is not None
        for record_title in project_alpha_labels
    )
