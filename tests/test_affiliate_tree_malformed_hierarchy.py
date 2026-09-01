"""Malformed corporate hierarchy must remain visible instead of disappearing."""

from __future__ import annotations

from lineageweave.affiliate_tree import AffiliationLeaf, CorporateEntityRow, build_affiliate_forest


def _leaf(entity_id: str, organization_name: str) -> AffiliationLeaf:
    return AffiliationLeaf(
        person_id="person-1",
        person_name="Ada West",
        person_side_code="our_side",
        organization_name=organization_name,
        corporate_entity_id=entity_id,
    )


def test_pure_parent_cycle_becomes_a_deterministic_disclosed_forest() -> None:
    entities = (
        CorporateEntityRow("alpha-id", "beta-id", "Alpha Corp", "company"),
        CorporateEntityRow("beta-id", "alpha-id", "Beta Corp", "company"),
    )

    forward = build_affiliate_forest(entities, (_leaf("beta-id", "Beta Corp"),))
    reversed_input = build_affiliate_forest(tuple(reversed(entities)), (_leaf("beta-id", "Beta Corp"),))

    assert [node.to_dict() for node in forward] == [node.to_dict() for node in reversed_input]
    assert len(forward) == 1
    assert forward[0].entity_id == "alpha-id"
    assert forward[0].hierarchy_issue == "cycle_parent_ignored"
    assert [child.entity_id for child in forward[0].children] == ["beta-id"]
    assert forward[0].children[0].people[0].person_id == "person-1"


def test_self_parent_is_kept_as_a_root_and_disclosed() -> None:
    forest = build_affiliate_forest(
        (CorporateEntityRow("solo-id", "solo-id", "Solo Corp", "company"),),
        (_leaf("solo-id", "Solo Corp"),),
    )

    assert len(forest) == 1
    assert forest[0].entity_id == "solo-id"
    assert forest[0].hierarchy_issue == "self_parent_ignored"
    assert forest[0].children == ()


def test_missing_parent_is_kept_and_disclosed_without_inventing_an_edge() -> None:
    forest = build_affiliate_forest(
        (CorporateEntityRow("child-id", "missing-parent", "Visible Child", "company"),),
        (_leaf("child-id", "Visible Child"),),
    )

    assert len(forest) == 1
    assert forest[0].entity_id == "child-id"
    assert forest[0].hierarchy_issue == "parent_not_available"
    assert forest[0].children == ()


def test_unavailable_entity_references_do_not_collapse_by_display_name() -> None:
    forest = build_affiliate_forest(
        (),
        (
            _leaf("missing-alpha", "Shared Display Name"),
            _leaf("missing-beta", "Shared Display Name"),
        ),
    )

    assert [(node.entity_id, node.entity_name, node.resolved) for node in forest] == [
        ("missing-alpha", "Shared Display Name", False),
        ("missing-beta", "Shared Display Name", False),
    ]
