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
                    "person_id": person.person_id,
                    "person_name": person.person_name,
                    "person_side_code": person.person_side_code,
                }
                for person in self.people
            ],
            "children": [child.to_dict() for child in self.children],
        }


def _people_for(affiliations: tuple[AffiliationLeaf, ...]) -> tuple[AffiliatePerson, ...]:
    """Deduplicate people on one node, sorted by name then id."""
    unique: dict[str, AffiliatePerson] = {}
    for leaf in affiliations:
        unique[leaf.person_id] = AffiliatePerson(
            person_id=leaf.person_id,
            person_name=leaf.person_name,
            person_side_code=leaf.person_side_code,
        )
    return tuple(sorted(unique.values(), key=lambda person: (person.person_name, person.person_id)))


def _needed_entity_ids(
    entities: dict[str, CorporateEntityRow],
    leaf_ids: set[str],
) -> set[str]:
    """Every ancestor of a resolved leaf, walking ``parent_entity_id``."""
    needed: set[str] = set()
    for leaf_id in leaf_ids:
        current = leaf_id
        while current and current not in needed:
            row = entities.get(current)
            if row is None:
                break
            needed.add(current)
            current = row.parent_entity_id or ""
    return needed


def build_affiliate_forest(
    entities: tuple[CorporateEntityRow, ...] | list[CorporateEntityRow],
    affiliations: tuple[AffiliationLeaf, ...] | list[AffiliationLeaf],
) -> tuple[AffiliateNode, ...]:
    """Ancestor forest covering every affiliation on a post.

    Resolved leaves pull in their parents. An entity that is neither a
    leaf nor an ancestor of one is omitted. Unresolved organization
    names become extra roots with ``resolved=False``.
    """
    entity_by_id = {row.entity_id: row for row in entities}
    resolved_leaves = [
        leaf for leaf in affiliations if leaf.corporate_entity_id and leaf.corporate_entity_id in entity_by_id
    ]
    needed = _needed_entity_ids(
        entity_by_id,
        {leaf.corporate_entity_id for leaf in resolved_leaves if leaf.corporate_entity_id},
    )

    people_by_entity: dict[str, list[AffiliationLeaf]] = {}
    for leaf in resolved_leaves:
        entity_id = leaf.corporate_entity_id
        if entity_id is None:
            continue
        people_by_entity.setdefault(entity_id, []).append(leaf)

    children_of: dict[str | None, list[str]] = {}
    for entity_id in needed:
        parent_id = entity_by_id[entity_id].parent_entity_id
        root_parent = parent_id if parent_id in needed else None
        children_of.setdefault(root_parent, []).append(entity_id)
    for child_ids in children_of.values():
        child_ids.sort(key=lambda entity_id: (entity_by_id[entity_id].entity_name, entity_id))

    def _build(entity_id: str) -> AffiliateNode:
        row = entity_by_id[entity_id]
        return AffiliateNode(
            entity_id=row.entity_id,
            entity_name=row.entity_name,
            entity_level_code=row.entity_level_code,
            resolved=True,
            people=_people_for(tuple(people_by_entity.get(entity_id, ()))),
            children=tuple(_build(child_id) for child_id in children_of.get(entity_id, ())),
        )

    resolved_roots = tuple(_build(entity_id) for entity_id in children_of.get(None, ()))

    unresolved_by_name: dict[str, list[AffiliationLeaf]] = {}
    for leaf in affiliations:
        if leaf.corporate_entity_id and leaf.corporate_entity_id in entity_by_id:
            continue
        name = leaf.organization_name.strip()
        if not name:
            continue
        unresolved_by_name.setdefault(name, []).append(leaf)

    unresolved_roots = tuple(
        AffiliateNode(
            entity_id=None,
            entity_name=name,
            entity_level_code=None,
            resolved=False,
            people=_people_for(tuple(leaves)),
            children=(),
        )
        for name, leaves in sorted(unresolved_by_name.items())
    )
    return resolved_roots + unresolved_roots
