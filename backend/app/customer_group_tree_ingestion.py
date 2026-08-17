"""Load the authorized customer-group forest from PostgreSQL."""

from __future__ import annotations

from typing import Any

import asyncpg

from lineageweave.customer_group_tree import (
    CatalogEntityRow,
    TreeAbbreviation,
    build_customer_group_forest,
)
from lineageweave.relation_verification import STATUS_CORROBORATED

from .knowledge_graph import labels_for_codes


async def fetch_customer_group_forest(
    conn: asyncpg.Connection,
    affiliated_entity_ids: list[str],
) -> list[dict[str, Any]]:
    """Authorized Group / Company / Plant forest for one account."""
    entity_rows = await conn.fetch(
        """
        select corporate_entity_id, parent_entity_id, entity_name, entity_level_code
        from corporate_entity
        """
    )
    entities = tuple(
        CatalogEntityRow(
            entity_id=str(row["corporate_entity_id"]),
            parent_entity_id=str(row["parent_entity_id"]) if row["parent_entity_id"] is not None else None,
            entity_name=row["entity_name"],
            entity_level_code=row["entity_level_code"],
        )
        for row in entity_rows
    )
    alias_rows = await conn.fetch(
        """
        select raw_organization_name, corporate_entity_id,
               verification_status_code, verification_evidence_url
          from abbreviation_tree_corroboration
         where verification_status_code = $1
           and corporate_entity_id is not null
        """,
        STATUS_CORROBORATED,
    )
    abbreviations = tuple(
        (
            str(row["corporate_entity_id"]),
            TreeAbbreviation(
                raw_organization_name=row["raw_organization_name"],
                verification_status_code=row["verification_status_code"],
                verification_evidence_url=row["verification_evidence_url"],
            ),
        )
        for row in alias_rows
    )
    forest = [
        node.to_dict()
        for node in build_customer_group_forest(entities, affiliated_entity_ids, abbreviations)
    ]
    await _attach_lookup_labels(conn, forest)
    return forest


def _collect_level_codes(nodes: list[dict[str, Any]]) -> list[str]:
    """Every entity-level code in the forest."""
    codes: list[str] = []
    for node in nodes:
        if node.get("entity_level_code"):
            codes.append(node["entity_level_code"])
        codes.extend(_collect_level_codes(node.get("children", [])))
    return codes


def _apply_lookup_labels(nodes: list[dict[str, Any]], labels: dict[str, str]) -> None:
    """Write display labels onto the JSON forest, falling back to the code."""
    for node in nodes:
        level = node.get("entity_level_code")
        node["entity_level_label"] = labels.get(level, level) if level else None
        _apply_lookup_labels(node.get("children", []), labels)


async def _attach_lookup_labels(conn: asyncpg.Connection, forest: list[dict[str, Any]]) -> None:
    """Hydrate ``entity_level_label`` from lookup rows."""
    _apply_lookup_labels(forest, await labels_for_codes(conn, _collect_level_codes(forest)))
