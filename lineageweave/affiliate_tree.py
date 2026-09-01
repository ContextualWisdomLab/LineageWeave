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
    """One organization in the rendered forest, with people and children.

    ``hierarchy_issue`` is present only when the source parent pointer could
    not safely become a tree edge. It discloses malformed or unavailable
    hierarchy evidence without changing entity-resolution truth.
    """

    entity_id: str | None
    entity_name: str
    entity_level_code: str | None
    resolved: bool
    people: tuple[AffiliatePerson, ...]
    children: tuple["AffiliateNode", ...]
    hierarchy_issue: str | None = None

    def to_dict(self) -> dict:
        """Return the JSON shape consumed by the product API and React panel."""
        payload = {
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
        if self.hierarchy_issue is not None:
            payload["hierarchy_issue"] = self.hierarchy_issue
        return payload


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
    """Return every available ancestor of a resolved affiliation leaf.

    The local ``seen`` set makes malformed cycles finite without letting one
    leaf suppress the ancestor walk for another leaf. Missing parents stop the
    walk; they are disclosed later instead of being invented as entity rows.
    """
    needed: set[str] = set()
    for leaf_id in leaf_ids:
        current = leaf_id
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            row = entities.get(current)
            if row is None:
                break
            needed.add(current)
            current = row.parent_entity_id or ""
    return needed


def _entity_sort_key(entities: dict[str, CorporateEntityRow], entity_id: str) -> tuple[str, str]:
    """Return the stable buyer-visible order used for roots and cycle breaks."""
    row = entities[entity_id]
    return (row.entity_name, row.entity_id)


def _safe_parent_links(
    entities: dict[str, CorporateEntityRow],
    needed: set[str],
) -> tuple[dict[str, str | None], dict[str, str]]:
    """Convert parent pointers into an acyclic forest without hiding defects.

    Self-parent pointers and unavailable parents become roots immediately. For
    a longer directed parent cycle, exactly one edge is ignored: the
    lexicographically first entity by ``(entity_name, entity_id)`` becomes the
    disclosed root. This preserves every authorized entity while making the
    result independent of database or input iteration order.
    """
    parent_by_id: dict[str, str | None] = {}
    issue_by_id: dict[str, str] = {}

    for entity_id in needed:
        parent_id = entities[entity_id].parent_entity_id
        if parent_id == entity_id:
            parent_by_id[entity_id] = None
            issue_by_id[entity_id] = "self_parent_ignored"
        elif parent_id and parent_id not in entities:
            parent_by_id[entity_id] = None
            issue_by_id[entity_id] = "parent_not_available"
        elif parent_id and parent_id in needed:
            parent_by_id[entity_id] = parent_id
        else:
            parent_by_id[entity_id] = None

    finalized: set[str] = set()
    for start_id in sorted(needed, key=lambda entity_id: _entity_sort_key(entities, entity_id)):
        if start_id in finalized:
            continue
        path: list[str] = []
        path_index: dict[str, int] = {}
        current: str | None = start_id
        while current is not None and current not in finalized:
            cycle_start = path_index.get(current)
            if cycle_start is not None:
                cycle = path[cycle_start:]
                cycle_root = min(cycle, key=lambda entity_id: _entity_sort_key(entities, entity_id))
                parent_by_id[cycle_root] = None
                issue_by_id[cycle_root] = "cycle_parent_ignored"
                break
            path_index[current] = len(path)
            path.append(current)
            current = parent_by_id[current]
        finalized.update(path)

    return parent_by_id, issue_by_id


def build_affiliate_forest(
    entities: tuple[CorporateEntityRow, ...] | list[CorporateEntityRow],
    affiliations: tuple[AffiliationLeaf, ...] | list[AffiliationLeaf],
) -> tuple[AffiliateNode, ...]:
    """Build the ancestor forest covering every affiliation on a post.

    Resolved leaves pull in their available parents. An entity that is neither
    a leaf nor an ancestor of one is omitted. Unresolved organization names
    become extra roots with ``resolved=False``. Malformed parent pointers never
    make an otherwise authorized affiliation disappear: the unsafe edge is
    omitted deterministically and the affected root carries ``hierarchy_issue``.
    """
    entity_by_id = {row.entity_id: row for row in entities}
    resolved_leaves = [
        leaf
        for leaf in affiliations
        if leaf.corporate_entity_id and leaf.corporate_entity_id in entity_by_id
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

    parent_by_id, hierarchy_issue_by_id = _safe_parent_links(entity_by_id, needed)
    children_of: dict[str | None, list[str]] = {}
    for entity_id in needed:
        children_of.setdefault(parent_by_id[entity_id], []).append(entity_id)
    for child_ids in children_of.values():
        child_ids.sort(key=lambda entity_id: _entity_sort_key(entity_by_id, entity_id))

    def _build(entity_id: str) -> AffiliateNode:
        """Materialize one already-cycle-safe hierarchy node recursively."""
        row = entity_by_id[entity_id]
        return AffiliateNode(
            entity_id=row.entity_id,
            entity_name=row.entity_name,
            entity_level_code=row.entity_level_code,
            resolved=True,
            people=_people_for(tuple(people_by_entity.get(entity_id, ()))),
            children=tuple(_build(child_id) for child_id in children_of.get(entity_id, ())),
            hierarchy_issue=hierarchy_issue_by_id.get(entity_id),
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
