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
from rdflib.namespace import RDF, SH, XSD

from lineageweave.ontology import project_project_mention_rdf, project_source_post_rdf

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
    data.add((post, LWn.bodyAvailable, Literal(True, datatype=XSD.boolean)))
    data.add((post, LWn.hasPostType, LWn.voiceOfCustomerType))
    data.add(
        (
            post,
            LWn.createdAt,
            Literal("2026-08-25T01:23:45+00:00", datatype=XSD.dateTime),
        )
    )
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


def test_shipped_shapes_conform_to_shacl_specification() -> None:
    """The shapes artifact itself must be valid SHACL before it may gate
    anything else -- validated with no data graph attached to it.
    """
    conforms, report_text = _conforms(_load_shapes())
    assert conforms, report_text


def test_sparql_constraints_declare_their_prefixes() -> None:
    """Portable SHACL-SPARQL constraints never rely on parser prefix fallback."""
    shapes = _load_shapes()
    constraints = set(shapes.subjects(RDF.type, SH.SPARQLConstraint))
    assert constraints
    assert all((constraint, SH.prefixes, None) in shapes for constraint in constraints)


def test_representative_db_projection_passes_validation() -> None:
    """A realistic projection of real schema rows validates cleanly."""
    conforms, report_text = _conforms(_representative_projection())
    assert conforms, report_text


def test_semantic_content_assertion_requires_source_post_provenance() -> None:
    """A semantic assertion without its source-post derivation fails closed."""
    data = _representative_projection()
    LWn = Namespace(LW)
    assertion = URIRef(LW + "semantic-assertion-alpha")
    post = URIRef(LW + "post-alpha")
    activity = URIRef(LW + "activity-alpha")
    data.add((assertion, RDF.type, LWn.SemanticContentAssertion))
    data.add((assertion, RDF.subject, post))
    data.add((assertion, RDF.predicate, LWn.describesActivity))
    data.add((assertion, RDF.object, activity))
    data.add((assertion, LWn.semanticEvidence, Literal("Synthetic activity evidence.")))
    conforms, report_text = _conforms(data)
    assert not conforms
    assert "wasDerivedFromPost" in report_text


def test_schema_shaped_project_row_projection_passes_validation() -> None:
    """The production projector emits the complete SHACL-governed chain."""
    data = project_project_mention_rdf(
        post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        post_title="Synthetic commissioning review",
        post_body="The synthetic source names the grid-upgrade project.",
        post_created_at=datetime(2026, 8, 25, 1, 23, 45, tzinfo=timezone.utc),
        voc_type_code="vop",
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
    post = URIRef(LW + "node/node_post/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1")
    assert (post, Namespace(LW).hasPostType, Namespace(LW).voiceOfPartnerType) in data


def test_missing_body_source_post_projection_passes_without_fabricated_text() -> None:
    """An evidenced missing body remains an empty literal and explicit false state."""
    data = project_source_post_rdf(
        post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
        post_title="Synthetic title-only record",
        post_body="",
        post_created_at=datetime(2026, 8, 25, 1, 23, 45, tzinfo=timezone.utc),
        voc_type_code="voc",
        source_stage_code="synthetic-stage",
        source_detail_state_code="synthetic-detail",
    )
    conforms, report_text = _conforms(data)
    assert conforms, report_text
    LWn = Namespace(LW)
    post = URIRef(LW + "node/node_post/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2")
    assert (post, LWn.postBody, Literal("")) in data
    assert (post, LWn.bodyAvailable, Literal(False, datatype=XSD.boolean)) in data
    assert (post, LWn.hasPostType, LWn.voiceOfCustomerType) in data


@pytest.mark.parametrize("post_body", ["\u00a0", "\u202f", "\u0085"])
def test_unicode_whitespace_body_matches_explicit_unavailable_state(
    post_body: str,
) -> None:
    """Unicode separators and NEL remain unavailable in RDF and SHACL."""
    data = project_source_post_rdf(
        post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3",
        post_title="Synthetic whitespace record",
        post_body=post_body,
        post_created_at=datetime(2026, 8, 25, 1, 23, 45, tzinfo=timezone.utc),
        voc_type_code="voc",
    )

    conforms, report_text = _conforms(data)

    assert conforms, report_text
    post = URIRef(LW + "node/node_post/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3")
    assert (
        post,
        Namespace(LW).bodyAvailable,
        Literal(False, datatype=XSD.boolean),
    ) in data


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
        "voc_type_code": "voc",
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
            lambda g: g.set(
                (
                    URIRef(LW + "post-alpha"),
                    URIRef(LW + "postTitle"),
                    Literal("   "),
                )
            ),
            "postTitle",
            id="whitespace-only-post-title",
        ),
        pytest.param(
            lambda g: g.set(
                (
                    URIRef(LW + "post-alpha"),
                    URIRef(LW + "bodyAvailable"),
                    Literal(False, datatype=XSD.boolean),
                )
            ),
            "bodyAvailable must be true",
            id="nonempty-body-marked-unavailable",
        ),
        pytest.param(
            lambda g: g.set(
                (
                    URIRef(LW + "post-alpha"),
                    URIRef(LW + "postBody"),
                    Literal(" \n\t"),
                )
            ),
            "bodyAvailable must be true",
            id="whitespace-body-marked-available",
        ),
        pytest.param(
            lambda g: g.add(
                (
                    URIRef(LW + "post-alpha"),
                    URIRef(LW + "sourceStageCode"),
                    Literal("   "),
                )
            ),
            "sourceStageCode",
            id="whitespace-only-source-stage-code",
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
