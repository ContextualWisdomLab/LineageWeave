"""Build the authorized customer-group forest operators navigate.

The post popup's affiliate tree is the ancestor forest of Keymen on one
record. This module is the complementary catalog view: every
``corporate_entity`` the account is affiliated with, plus ancestors and
descendants, using the existing Group / Company / Plant codes
(``corporate_entity_level``). A sibling the account is not affiliated
with stays omitted -- affiliation is not a guessed parent
(Bhattacharya & Getoor, 2007).

Corroborated abbreviations attach as SKOS alternative labels
(Miles & Bechhofer, 2009). Uncorroborated rows never appear here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogEntityRow:
    """One ``corporate_entity`` row the forest builder needs."""

    entity_id: str
    parent_entity_id: str | None
    entity_name: str
    entity_level_code: str


@dataclass(frozen=True)
class TreeAbbreviation:
    """One Searxng-corroborated alternative label on a catalog node."""

    raw_organization_name: str
    verification_status_code: str
    verification_evidence_url: str | None


@dataclass(frozen=True)
class CustomerGroupNode:
    """One Group / Company / Plant node in the authorized forest."""

    entity_id: str
    entity_name: str
    entity_level_code: str
    children: tuple["CustomerGroupNode", ...]
    abbreviations: tuple[TreeAbbreviation, ...]

    def to_dict(self) -> dict:
        """JSON shape the product API and React navigator consume."""
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_level_code": self.entity_level_code,
            "abbreviations": [
                {
                    "raw_organization_name": alias.raw_organization_name,
                    "verification_status_code": alias.verification_status_code,
                    "verification_evidence_url": alias.verification_evidence_url,
                }
                for alias in self.abbreviations
            ],
            "children": [child.to_dict() for child in self.children],
        }


def authorized_catalog_ids(
    entities: tuple[CatalogEntityRow, ...] | list[CatalogEntityRow],
    affiliated_ids: tuple[str, ...] | list[str] | set[str],
) -> set[str]:
    """Affiliated rows plus every ancestor and descendant.

    An affiliated company therefore surfaces its group parent and plant
    children. A catalog row the account does not touch stays out.
    """
    entity_by_id = {row.entity_id: row for row in entities}
    children_of: dict[str | None, list[str]] = {}
    for row in entities:
        children_of.setdefault(row.parent_entity_id, []).append(row.entity_id)

    needed: set[str] = set()
    for affiliated_id in affiliated_ids:
        if affiliated_id not in entity_by_id:
            continue
        current: str | None = affiliated_id
        while current and current not in needed:
            row = entity_by_id.get(current)
            if row is None:
                break
            needed.add(current)
            current = row.parent_entity_id
        stack = [affiliated_id]
        while stack:
            entity_id = stack.pop()
            for child_id in children_of.get(entity_id, ()):
                if child_id not in needed:
                    needed.add(child_id)
                    stack.append(child_id)
    return needed


def build_customer_group_forest(
    entities: tuple[CatalogEntityRow, ...] | list[CatalogEntityRow],
    affiliated_ids: tuple[str, ...] | list[str] | set[str],
    abbreviations: tuple[tuple[str, TreeAbbreviation], ...] | list[tuple[str, TreeAbbreviation]] = (),
) -> tuple[CustomerGroupNode, ...]:
    """Authorized Group / Company / Plant forest for one account.

    ``abbreviations`` pairs a catalog entity id with a corroborated
    alternative label. Labels for an omitted entity are dropped.
    """
    entity_by_id = {row.entity_id: row for row in entities}
    needed = authorized_catalog_ids(entities, affiliated_ids)
    aliases_by_entity: dict[str, list[TreeAbbreviation]] = {}
    for entity_id, alias in abbreviations:
        if entity_id in needed:
            aliases_by_entity.setdefault(entity_id, []).append(alias)
    for alias_list in aliases_by_entity.values():
        alias_list.sort(key=lambda alias: alias.raw_organization_name)

    children_of: dict[str | None, list[str]] = {}
    for entity_id in needed:
        parent_id = entity_by_id[entity_id].parent_entity_id
        root_parent = parent_id if parent_id in needed else None
        children_of.setdefault(root_parent, []).append(entity_id)
    for child_ids in children_of.values():
        child_ids.sort(key=lambda entity_id: (entity_by_id[entity_id].entity_name, entity_id))

    def _build(entity_id: str) -> CustomerGroupNode:
        row = entity_by_id[entity_id]
        return CustomerGroupNode(
            entity_id=row.entity_id,
            entity_name=row.entity_name,
            entity_level_code=row.entity_level_code,
            abbreviations=tuple(aliases_by_entity.get(entity_id, ())),
            children=tuple(_build(child_id) for child_id in children_of.get(entity_id, ())),
        )

    return tuple(_build(entity_id) for entity_id in children_of.get(None, ()))
