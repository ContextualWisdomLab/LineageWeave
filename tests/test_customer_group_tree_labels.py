"""Lookup-label helpers for the customer-group JSON forest."""

from __future__ import annotations

from backend.app.customer_group_tree_ingestion import _apply_lookup_labels, _collect_level_codes


def test_collect_level_codes_walks_nested_children() -> None:
    codes = _collect_level_codes(
        [
            {
                "entity_level_code": "group",
                "children": [
                    {
                        "entity_level_code": "company",
                        "children": [{"entity_level_code": "plant", "children": []}],
                    }
                ],
            }
        ]
    )
    assert codes == ["group", "company", "plant"]


def test_apply_lookup_labels_falls_back_to_the_code() -> None:
    forest = [
        {
            "entity_level_code": "group",
            "children": [{"entity_level_code": "company", "children": []}],
        },
        {"entity_level_code": None, "children": []},
    ]
    _apply_lookup_labels(forest, {"group": "Group"})
    assert forest[0]["entity_level_label"] == "Group"
    assert forest[0]["children"][0]["entity_level_label"] == "company"
    assert forest[1]["entity_level_label"] is None
