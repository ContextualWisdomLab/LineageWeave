"""Real correctness check for docs/ontology/lineageweave-kg.ttl (ADR 0004):
the ontology's vocabulary must not silently drift from the
`common_lookup_value` rows the demo stack actually seeds. This is a
round-trip against `scripts/seed_demo_data.py`'s own committed SQL, not
a live database -- the two files are the actual pair that must stay in
sync, and this test fails the moment either one adds or renames a code
the other doesn't know about.
"""

from __future__ import annotations

import re
from pathlib import Path

from lineageweave.ontology import LW, all_declared_lookup_codes, iri_for_lookup_code, load_ontology
from rdflib.namespace import RDFS, SKOS

_SEED_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo_data.py"

# The categories this ontology covers (ADR 0004's scope). seed_demo_data.py
# also seeds categories this ontology deliberately does not model yet
# (post_visibility, voc_type, permission, ticket_status) -- those are
# real, expected gaps, not a test bug.
_ONTOLOGY_COVERED_CATEGORIES = frozenset(
    {"node_type", "edge_type", "entity_relationship_type", "person_side", "corporate_entity_level"}
)

_INSERT_TUPLE_PATTERN = re.compile(r"\('([a-z_]+)',\s*'([a-z_]+)'")


def _seeded_lookup_codes_for_covered_categories() -> set[str]:
    """Every `(lookup_category, lookup_code)` pair seed_demo_data.py's own
    SQL literally inserts, filtered to the categories this ontology
    covers. Parsed from source, not executed -- this is a static
    consistency check between two committed files, not a live-database
    test.
    """
    source = _SEED_SCRIPT_PATH.read_text()
    return {
        code
        for category, code in _INSERT_TUPLE_PATTERN.findall(source)
        if category in _ONTOLOGY_COVERED_CATEGORIES
    }


def test_ontology_parses_as_valid_turtle() -> None:
    graph = load_ontology()
    assert len(graph) > 0


def test_every_seeded_lookup_code_is_declared_in_the_ontology() -> None:
    seeded = _seeded_lookup_codes_for_covered_categories()
    declared = all_declared_lookup_codes()
    missing_from_ontology = seeded - declared
    assert not missing_from_ontology, (
        f"seed_demo_data.py seeds these codes with no matching ontology term: {missing_from_ontology}"
    )


def test_ontology_declares_no_lookup_code_the_seed_script_does_not_use() -> None:
    seeded = _seeded_lookup_codes_for_covered_categories()
    declared = all_declared_lookup_codes()
    stale_in_ontology = declared - seeded
    assert not stale_in_ontology, (
        f"lineageweave-kg.ttl declares codes seed_demo_data.py never inserts: {stale_in_ontology}"
    )


def test_iri_for_lookup_code_resolves_a_real_term() -> None:
    assert iri_for_lookup_code("edge_mention") == str(LW.mentions)
    assert iri_for_lookup_code("rel_voc") == str(LW.hasVocRelationship)


def test_iri_for_lookup_code_returns_none_for_an_undeclared_code() -> None:
    assert iri_for_lookup_code("not_a_real_lookup_code") is None


def test_mentions_property_domain_and_range_match_the_schema() -> None:
    """`mentions` goes Post -> Person, matching post_person_mention's
    actual foreign keys -- not just any two classes."""
    graph = load_ontology()
    assert (LW.mentions, RDFS.domain, LW.Post) in graph
    assert (LW.mentions, RDFS.range, LW.Person) in graph


def test_corporate_entity_level_hierarchy_is_broadest_first() -> None:
    """Group is broader than Company is broader than Plant -- the
    Samsung -> Samsung Electronics Korea -> ... -> plant direction the
    product brief describes."""
    graph = load_ontology()
    assert (LW.CompanyLevel, SKOS.broader, LW.GroupLevel) in graph
    assert (LW.PlantLevel, SKOS.broader, LW.CompanyLevel) in graph
    assert (LW.GroupLevel, SKOS.broader, LW.CompanyLevel) not in graph
