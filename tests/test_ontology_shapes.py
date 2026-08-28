"""Closed-world SHACL validation of the LineageWeave knowledge-graph
ontology (ADR 0207 decision 10).

OWL's open-world semantics infers; it does not verify that projected
data arrived complete and in range (Knublauch & Kontokostas, 2017).
`docs/ontology/lineageweave-kg-shapes.ttl` carries exactly that
verification, and this module proves it works in both directions:

- the shipped shapes graph conforms to the SHACL specification itself;
- a representative post/mention projection passes;
- the same projection with duplicate or above-range confidence -- or a missing
  required title -- is rejected, naming the violated constraint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from pyshacl import validate as shacl_validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from lineageweave.ontology import project_product_relation_rdf, project_project_mention_rdf

ROOT = Path(__file__).resolve().parents[1]
KG_PATH = ROOT / "docs" / "ontology" / "lineageweave-kg.ttl"
SHAPES_PATH = ROOT / "docs" / "ontology" / "lineageweave-kg-shapes.ttl"

LW = "https://contextualwisdomlab.github.io/LineageWeave/ontology#"


def _load_kg() -> Graph:
    """Parse the source ontology graph fresh."""
    return Graph().parse(KG_PATH, format="turtle")


def _load_shapes() -> Graph:
    """Parse the SHACL shapes graph fresh."""
    return Graph().parse(SHAPES_PATH, format="turtle")


def _conforms(data: Graph) -> tuple[bool, str]:
    """Run pyshacl over ``data`` against the shipped shapes; return the
    verdict plus the human-readable report text for assertions."""
    conforms, _, report_text = shacl_validate(
        data_graph=data,
        shacl_graph=_load_shapes(),
        ont_graph=_load_kg(),
        inference="none",
        advanced=True,
    )
    return bool(conforms), report_text


def _representative_projection() -> Graph:
    """Build one minimal but realistic DB-to-RDF projection: a post with
    every required attribute, a person, an entity, an our-side person,
    and a project mention whose evidence chain is intact.
    """
    data = _load_kg()
    LWn = Namespace(LW)
    post = URIRef(LW + "post-alpha")
    data.add((post, RDF.type, LWn.Post))
    data.add((post, LWn.postTitle, Literal("Line 3 downtime window")))
    data.add((post, LWn.postBody, Literal("Customer reported a stoppage after changeover.")))
    data.add(
        (
            post,
            LWn.createdAt,
            Literal("2026-08-25T01:23:45+00:00", datatype=XSD.dateTime),
        )
    )
    voice_assignment = URIRef(LW + "voice-assignment/post-alpha/voc")
    data.add((voice_assignment, RDF.type, LWn.VoiceAssignment))
    data.add((voice_assignment, LWn.assignedVoiceType, LWn.voiceOfCustomerType))
    data.add((voice_assignment, LWn.primaryVoiceAssignment, Literal(True)))
    data.add((voice_assignment, LWn.voiceAssignmentEvidence, post))
    person = URIRef(LW + "person-okonkwo")
    data.add((person, RDF.type, LWn.Person))
    data.add((person, LWn.personName, Literal("Sam Okonkwo")))
    entity = URIRef(LW + "entity-acme")
    data.add((entity, RDF.type, LWn.CorporateEntity))
    data.add((entity, LWn.entityName, Literal("Acme Electronics Korea")))
    data.add((entity, LWn.entityCode, Literal("ACME-KR")))
    our_side = URIRef(LW + "person-our-side")
    data.add((our_side, RDF.type, LWn.OurSidePerson))
    # Our-side persons are SHACL instances of :Person through the
    # subclass chain, so the required name applies to them as well --
    # exactly like cataloged_person.person_name's NOT NULL.
    data.add((our_side, LWn.personName, Literal("Dana Whitfield")))
    mention = URIRef(LW + "mention-alpha")
    project = URIRef(LW + "project-alpha")
    data.add((project, RDF.type, LWn.Project))
    data.add((mention, RDF.type, LWn.ProjectMention))
    data.add((mention, RDF.subject, post))
    data.add((mention, RDF.predicate, LWn.mentionsProject))
    data.add((mention, RDF.object, project))
    data.add(
        (
            mention,
            LWn.semanticConfidence,
            Literal("0.87", datatype=XSD.decimal),
        )
    )
    data.add((mention, LWn.projectEvidence, Literal("proj-alpha kickoff cited verbatim.")))
    return data


def test_voice_assignment_requires_source_evidence() -> None:
    """A projected Voice assignment without its authorized source post fails closed."""
    data = _representative_projection()
    LWn = Namespace(LW)
    assignment = URIRef(LW + "voice-assignment/post-alpha/voc")
    data.remove((assignment, LWn.voiceAssignmentEvidence, None))

    conforms, report = _conforms(data)

    assert conforms is False
    assert "voice assignment evidence" in report.lower()


def test_shipped_shapes_conform_to_shacl_specification() -> None:
    """The shapes artifact itself must be valid SHACL before it may gate
    anything else -- validated with no data graph attached to it.
    """
    conforms, report_text = _conforms(_load_shapes())
    assert conforms, report_text


def test_representative_db_projection_passes_validation() -> None:
    """A realistic projection of real schema rows validates cleanly."""
    conforms, report_text = _conforms(_representative_projection())
    assert conforms, report_text


def test_schema_shaped_project_row_projection_passes_validation() -> None:
    """The production projector emits the complete SHACL-governed chain."""
    data = project_project_mention_rdf(
        post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        post_title="Synthetic commissioning review",
        post_body="The synthetic source names the grid-upgrade project.",
        post_created_at=datetime(2026, 8, 25, 1, 23, 45, tzinfo=timezone.utc),
        project_key="grid-upgrade",
        project_name="Grid Upgrade",
        evidence_text="grid-upgrade project",
        confidence=Decimal("0.870"),
        mention_created_at=datetime(2026, 8, 25, 1, 24, tzinfo=timezone.utc),
    )
    conforms, report_text = _conforms(data)
    assert conforms, report_text
    LWn = Namespace(LW)
    mention = URIRef(
        LW + "statement/project-mention/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1/grid-upgrade"
    )
    project = URIRef(
        LW + "node/node_project/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1/grid-upgrade"
    )
    assert (mention, RDF.subject, None) in data
    assert (mention, RDF.predicate, LWn.mentionsProject) in data
    assert (mention, RDF.object, project) in data


def test_product_relation_projection_passes_validation_and_closed_codes() -> None:
    """The production projector emits a complete evidence-bound relation."""
    data = project_product_relation_rdf(
        post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        mention_ordinal=0,
        product_id="synthetic-product",
        target_kind_code="project",
        target_id="synthetic-project",
        relation_type_code="used_by_project",
        evidence_text="Synthetic Product supports Synthetic Project",
        evidence_input_sha256="a" * 64,
        post_title="Synthetic relation source",
        post_body="Synthetic Product supports Synthetic Project",
        post_created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
    )
    conforms, report_text = _conforms(data)
    assert conforms, report_text
    with pytest.raises(ValueError, match="relation type"):
        project_product_relation_rdf(
            post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
            mention_ordinal=0,
            product_id="synthetic-product",
            target_kind_code="project",
            target_id="synthetic-project",
            relation_type_code="concerns_product",
            evidence_text="Synthetic evidence",
            evidence_input_sha256="a" * 64,
            post_title="Synthetic relation source",
            post_body="Synthetic evidence",
            post_created_at=datetime(2026, 8, 27, tzinfo=timezone.utc),
        )


def test_product_relation_assertion_identity_retains_distinct_predicates() -> None:
    """Two supported claims for one target remain separate RDF assertions."""
    kwargs = {
        "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        "mention_ordinal": 0,
        "product_id": "synthetic-product",
        "target_kind_code": "operations_fact",
        "target_id": "synthetic-fact",
        "evidence_text": "Synthetic Product changes the observed fact",
        "evidence_input_sha256": "a" * 64,
        "post_title": "Synthetic relation source",
        "post_body": "Synthetic Product changes the observed fact",
        "post_created_at": datetime(2026, 8, 27, tzinfo=timezone.utc),
    }
    data = project_product_relation_rdf(
        **kwargs, relation_type_code="concerns_product"
    ) + project_product_relation_rdf(
        **kwargs, relation_type_code="changes_product"
    )

    LWn = Namespace(LW)
    assertions = set(data.subjects(RDF.type, LWn.ProductRelationAssertion))
    assert len(assertions) == 2
    assert {
        data.value(assertion, RDF.predicate) for assertion in assertions
    } == {LWn.concernsProduct, LWn.changesProduct}


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"post_id": "not-a-uuid"}, "badly formed"),
        ({"project_key": "Grid Upgrade"}, "already be normalized"),
        ({"evidence_text": " "}, "evidence_text must be non-empty"),
        (
            {"post_created_at": datetime(2026, 8, 25, 1, 23, 45)},
            "post_created_at must be timezone-aware",
        ),
        ({"confidence": "not-a-number"}, "confidence must be a decimal"),
        ({"confidence": "1.001"}, "confidence must be a decimal"),
    ],
)
def test_project_row_projection_rejects_invalid_source_values(
    override: dict[str, object], message: str
) -> None:
    """Malformed DB-shaped values fail before an RDF assertion is emitted."""
    values: dict[str, object] = {
        "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        "post_title": "Synthetic commissioning review",
        "post_body": "The synthetic source names the grid-upgrade project.",
        "post_created_at": datetime(2026, 8, 25, 1, 23, 45, tzinfo=timezone.utc),
        "project_key": "grid-upgrade",
        "project_name": "Grid Upgrade",
        "evidence_text": "grid-upgrade project",
        "confidence": Decimal("0.870"),
        "mention_created_at": datetime(2026, 8, 25, 1, 24, tzinfo=timezone.utc),
    }
    values.update(override)
    with pytest.raises(ValueError, match=message):
        project_project_mention_rdf(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("mutation", "expected_fragment"),
    [
        pytest.param(
            lambda g: g.remove(
                (
                    URIRef(LW + "post-alpha"),
                    URIRef(LW + "postTitle"),
                    None,
                )
            ),
            "postTitle",
            id="missing-required-post-title",
        ),
        pytest.param(
            lambda g: g.remove(
                (
                    URIRef(LW + "mention-alpha"),
                    RDF.subject,
                    None,
                )
            ),
            "mentioned by post",
            id="missing-project-mention-subject",
        ),
        pytest.param(
            lambda g: g.set(
                (
                    URIRef(LW + "mention-alpha"),
                    RDF.predicate,
                    URIRef(LW + "mentionsTeam"),
                )
            ),
            "project mention predicate",
            id="wrong-project-mention-predicate",
        ),
        pytest.param(
            lambda g: g.set(
                (
                    URIRef(LW + "mention-alpha"),
                    URIRef(LW + "semanticConfidence"),
                    Literal("1.5", datatype=XSD.decimal),
                )
            ),
            "semanticConfidence",
            id="confidence-above-one",
        ),
        pytest.param(
            lambda g: g.add(
                (
                    URIRef(LW + "mention-alpha"),
                    URIRef(LW + "semanticConfidence"),
                    Literal("0.5", datatype=XSD.decimal),
                )
            ),
            "semanticConfidence",
            id="duplicate-confidence",
        ),
        pytest.param(
            lambda g: g.add(
                (
                    URIRef(LW + "person-our-side"),
                    RDF.type,
                    URIRef(LW + "CounterpartyPerson"),
                )
            ),
            "OurSidePersonShape",
            id="disjoint-person-side",
        ),
        pytest.param(
            lambda g: g.remove(
                (
                    URIRef(LW + "entity-acme"),
                    URIRef(LW + "entityCode"),
                    None,
                )
            ),
            "entityCode",
            id="missing-entity-code",
        ),
    ],
)
def test_violations_are_rejected_with_the_right_constraint_name(
    mutation, expected_fragment: str
) -> None:
    """Each broken projection fails closed and the report names the
    property or shape that was violated, so operators see which column
    projection drifted instead of a bare boolean.
    """
    data = _representative_projection()
    mutation(data)
    conforms, report_text = _conforms(data)
    assert not conforms
    assert expected_fragment in report_text


def test_confidence_boundary_values_are_inclusive() -> None:
    """Exactly 0.0 and 1.0 are legal -- the bound is [0.0, 1.0]
    inclusive per ADR 0207 decision 10.
    """
    for value in ("0.0", "1.0"):
        data = _representative_projection()
        data.set(
            (
                URIRef(LW + "mention-alpha"),
                URIRef(LW + "semanticConfidence"),
                Literal(value, datatype=XSD.decimal),
            )
        )
        conforms, report_text = _conforms(data)
        assert conforms, f"{value} rejected:\n{report_text}"


def test_derived_voice_assertion_requires_receipt_and_ordered_source_span() -> None:
    """Derived voice RDF cannot omit the receipt or its exact source span."""
    data = _representative_projection()
    voice = URIRef(LW + "voice-assertion-alpha")
    post = URIRef(LW + "post-alpha")
    prov = Namespace("http://www.w3.org/ns/prov#")
    LWn = Namespace(LW)
    for predicate, value in (
        (RDF.type, LWn.PostVoiceClassificationAssertion),
        (LWn.voiceConceptCode, Literal("voc")),
        (LWn.voiceAssertionStatus, Literal("derived")),
        (LWn.voiceEvidenceDigest, Literal("a" * 64)),
        (LWn.sourceRevisionDigest, Literal("b" * 64)),
        (prov.wasDerivedFrom, post),
    ):
        data.add((voice, predicate, value))

    conforms, report_text = _conforms(data)
    assert not conforms
    assert "orchestratorModelReceipt" in report_text

    data.add((voice, LWn.orchestratorModelReceipt, Literal("synthetic-receipt")))
    data.add((voice, LWn.evidenceSpanStart, Literal(0, datatype=XSD.integer)))
    data.add((voice, LWn.evidenceSpanEnd, Literal(12, datatype=XSD.integer)))
    conforms, report_text = _conforms(data)
    assert conforms, report_text


@pytest.mark.parametrize("voice_code", ("vos", "voe", "vob", "vor", "voi", "voso", "vops"))
def test_expanded_source_post_voice_codes_conform(voice_code: str) -> None:
    """ADR 0246 post codes validate without becoming organization relations."""
    data = _representative_projection()
    LWn = Namespace(LW)
    voice = URIRef(LW + f"voice-assertion-{voice_code}")
    for predicate, value in (
        (RDF.type, LWn.PostVoiceClassificationAssertion),
        (LWn.voiceConceptCode, Literal(voice_code)),
        (LWn.voiceAssertionStatus, Literal("source")),
        (LWn.voiceEvidenceDigest, Literal("a" * 64)),
        (LWn.sourceRevisionDigest, Literal("b" * 64)),
        (Namespace("http://www.w3.org/ns/prov#").wasDerivedFrom, URIRef(LW + "post-alpha")),
    ):
        data.add((voice, predicate, value))
    conforms, report_text = _conforms(data)
    assert conforms, report_text
