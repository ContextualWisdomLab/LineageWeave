"""Build a corporate affiliate tree from parent-pointer entities.

The product popup's Affiliate Tree is the ancestor forest of every
organization a post's Keymen are affiliated with -- not the full
``corporate_entity`` table. A sibling the post never mentions is omitted
so the buyer sees only the hierarchy that this record actually touches.

Unresolved affiliation names (no ``corporate_entity_id``) stay as their
own roots. Inventing a parent for "Northridge Grid" would be a guessed
hierarchy link; a missing resolution is not a tree edge (Bhattacharya &
Getoor, 2007, candidate-generation stage -- already the grounding for
``corporate_hierarchy_resolution``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorporateEntityRow:
    """One ``corporate_entity`` row the tree builder needs."""

    entity_id: str
    parent_entity_id: str | None
    entity_name: str
    entity_level_code: str


@dataclass(frozen=True)
class AffiliationLeaf:
    """One person-to-organization attachment that seeds the forest."""

    person_id: str
    person_name: str
    person_side_code: str
    organization_name: str
    corporate_entity_id: str | None


@dataclass(frozen=True)
class AffiliatePerson:
    """A Keyman hanging off one organization node."""

    person_id: str
    person_name: str
    person_side_code: str


@dataclass(frozen=True)
class AffiliateNode:
    """One organization in the rendered forest, with people and children."""

    entity_id: str | None
    entity_name: str
    entity_level_code: str | None
    resolved: bool
    people: tuple[AffiliatePerson, ...]
    children: tuple["AffiliateNode", ...]

    def to_dict(self) -> dict:
        """JSON shape the product API and React panel consume."""
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_level_code": self.entity_level_code,
            "resolved": self.resolved,
            "people": [
                {
                    "person_id": affiliate_person.person_id,
                    "person_name": affiliate_person.person_name,
                    "person_side_code": affiliate_person.person_side_code,
                }
                for affiliate_person in self.people
            ],
            "children": [child_node.to_dict() for child_node in self.children],
        }


def _people_for(
    affiliation_leaves: tuple[AffiliationLeaf, ...],
) -> tuple[AffiliatePerson, ...]:
    """Deduplicate people on one node, sorted by name then id."""
    affiliate_people_by_id: dict[str, AffiliatePerson] = {}
    for affiliation_leaf in affiliation_leaves:
        affiliate_people_by_id[affiliation_leaf.person_id] = AffiliatePerson(
            person_id=affiliation_leaf.person_id,
            person_name=affiliation_leaf.person_name,
            person_side_code=affiliation_leaf.person_side_code,
        )
    return tuple(
        sorted(
            affiliate_people_by_id.values(),
            key=lambda affiliate_person: (
                affiliate_person.person_name,
                affiliate_person.person_id,
            ),
        )
    )


def _needed_entity_ids(
    corporate_entities_by_id: dict[str, CorporateEntityRow],
    leaf_entity_ids: set[str],
) -> set[str]:
    """Every ancestor of a resolved leaf, walking ``parent_entity_id``."""
    needed_entity_ids: set[str] = set()
    for leaf_entity_id in leaf_entity_ids:
        current_entity_id = leaf_entity_id
        while current_entity_id and current_entity_id not in needed_entity_ids:
            corporate_entity_row = corporate_entities_by_id.get(current_entity_id)
            if corporate_entity_row is None:
                break
            needed_entity_ids.add(current_entity_id)
            current_entity_id = corporate_entity_row.parent_entity_id or ""
    return needed_entity_ids


def build_affiliate_forest(
    corporate_entities: tuple[CorporateEntityRow, ...] | list[CorporateEntityRow],
    affiliation_leaves: tuple[AffiliationLeaf, ...] | list[AffiliationLeaf],
) -> tuple[AffiliateNode, ...]:
    """Ancestor forest covering every affiliation on a post.

    Resolved leaves pull in their parents. An entity that is neither a
    leaf nor an ancestor of one is omitted. Unresolved organization
    names become extra roots with ``resolved=False``.
    """
    corporate_entities_by_id = {
        corporate_entity_row.entity_id: corporate_entity_row
        for corporate_entity_row in corporate_entities
    }
    resolved_affiliation_leaves = [
        affiliation_leaf
        for affiliation_leaf in affiliation_leaves
        if affiliation_leaf.corporate_entity_id
        and affiliation_leaf.corporate_entity_id in corporate_entities_by_id
    ]
    needed_entity_ids = _needed_entity_ids(
        corporate_entities_by_id,
        {
            affiliation_leaf.corporate_entity_id
            for affiliation_leaf in resolved_affiliation_leaves
            if affiliation_leaf.corporate_entity_id
        },
    )

    affiliation_leaves_by_entity_id: dict[str, list[AffiliationLeaf]] = {}
    for affiliation_leaf in resolved_affiliation_leaves:
        entity_id = affiliation_leaf.corporate_entity_id
        if entity_id is None:
            continue
        affiliation_leaves_by_entity_id.setdefault(entity_id, []).append(
            affiliation_leaf
        )

    affiliate_children_by_parent_id: dict[str | None, list[str]] = {}
    for entity_id in needed_entity_ids:
        parent_entity_id = corporate_entities_by_id[entity_id].parent_entity_id
        forest_parent_id = (
            parent_entity_id if parent_entity_id in needed_entity_ids else None
        )
        affiliate_children_by_parent_id.setdefault(forest_parent_id, []).append(
            entity_id
        )
    for child_entity_ids in affiliate_children_by_parent_id.values():
        child_entity_ids.sort(
            key=lambda entity_id: (
                corporate_entities_by_id[entity_id].entity_name,
                entity_id,
            )
        )

    def _build_affiliate_node(entity_id: str) -> AffiliateNode:
        """Build one resolved affiliate node and its descendants."""
        corporate_entity_row = corporate_entities_by_id[entity_id]
        return AffiliateNode(
            entity_id=corporate_entity_row.entity_id,
            entity_name=corporate_entity_row.entity_name,
            entity_level_code=corporate_entity_row.entity_level_code,
            resolved=True,
            people=_people_for(
                tuple(affiliation_leaves_by_entity_id.get(entity_id, ()))
            ),
            children=tuple(
                _build_affiliate_node(child_entity_id)
                for child_entity_id in affiliate_children_by_parent_id.get(
                    entity_id, ()
                )
            ),
        )

    resolved_root_nodes = tuple(
        _build_affiliate_node(entity_id)
        for entity_id in affiliate_children_by_parent_id.get(None, ())
    )

    unresolved_affiliations_by_name: dict[str, list[AffiliationLeaf]] = {}
    for affiliation_leaf in affiliation_leaves:
        if (
            affiliation_leaf.corporate_entity_id
            and affiliation_leaf.corporate_entity_id in corporate_entities_by_id
        ):
            continue
        organization_name = affiliation_leaf.organization_name.strip()
        if not organization_name:
            continue
        unresolved_affiliations_by_name.setdefault(organization_name, []).append(
            affiliation_leaf
        )

    unresolved_root_nodes = tuple(
        AffiliateNode(
            entity_id=None,
            entity_name=organization_name,
            entity_level_code=None,
            resolved=False,
            people=_people_for(tuple(unresolved_affiliation_leaves)),
            children=(),
        )
        for organization_name, unresolved_affiliation_leaves in sorted(
            unresolved_affiliations_by_name.items()
        )
    )
    return resolved_root_nodes + unresolved_root_nodes
