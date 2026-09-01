"""Load a post's Keyman affiliations into the affiliate-tree forest."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg

from lineageweave.affiliate_tree import AffiliationLeaf, CorporateEntityRow, build_affiliate_forest
from lineageweave.organization_alias import attach_organization_aliases
from lineageweave.voc_evidence import first_excerpt_for, sentence_excerpts

from .knowledge_graph import fetch_post_keymen, labels_for_codes
from .organization_name_resolution_ingestion import fetch_corroborated_organization_aliases


async def fetch_affiliate_forest(conn: asyncpg.Connection, post_id: str) -> list[dict[str, Any]]:
    """Ancestor forest of only the organizations this post's Keymen touch.

    Read the post's stored affiliations without alias decoration first. Only
    unresolved organization names from that post are allowed to select alias
    rows; if a corroborated alias resolves one of them, Keymen are reloaded
    against that bounded alias snapshot. The hierarchy query then starts from
    the resolved corporate-entity identifiers and walks only their ancestors.
    """
    raw_keymen = await fetch_post_keymen(conn, post_id, organization_aliases=())
    unresolved_names = tuple(
        sorted(
            {
                affiliation["organization_name"].strip()
                for person in raw_keymen
                for affiliation in person["affiliations"]
                if affiliation["corporate_entity_id"] is None
                and affiliation["organization_name"].strip()
            }
        )
    )
    aliases = (
        await fetch_corroborated_organization_aliases(
            conn,
            organization_names=unresolved_names,
        )
        if unresolved_names
        else ()
    )
    keymen = (
        await fetch_post_keymen(conn, post_id, organization_aliases=aliases)
        if aliases
        else raw_keymen
    )

    leaves: list[AffiliationLeaf] = []
    for person in keymen:
        for affiliation in person["affiliations"]:
            leaves.append(
                AffiliationLeaf(
                    person_id=person["person_id"],
                    person_name=person["person_name"],
                    person_side_code=person["person_side_code"],
                    organization_name=affiliation["organization_name"],
                    corporate_entity_id=affiliation["corporate_entity_id"],
                )
            )

    resolved_entity_ids = sorted(
        {
            UUID(leaf.corporate_entity_id)
            for leaf in leaves
            if leaf.corporate_entity_id is not None
        },
        key=str,
    )
    entity_rows = []
    if resolved_entity_ids:
        entity_rows = await conn.fetch(
            """
            with recursive affiliate_entity as (
                select corporate_entity_id, parent_entity_id, entity_name, entity_level_code
                from corporate_entity
                where corporate_entity_id = any($1::uuid[])

                union

                select parent.corporate_entity_id,
                       parent.parent_entity_id,
                       parent.entity_name,
                       parent.entity_level_code
                from corporate_entity parent
                join affiliate_entity child
                  on child.parent_entity_id = parent.corporate_entity_id
            )
            select corporate_entity_id, parent_entity_id, entity_name, entity_level_code
            from affiliate_entity
            order by entity_name, corporate_entity_id
            """,
            resolved_entity_ids,
        )
    entities = tuple(
        CorporateEntityRow(
            entity_id=str(row["corporate_entity_id"]),
            parent_entity_id=str(row["parent_entity_id"]) if row["parent_entity_id"] is not None else None,
            entity_name=row["entity_name"],
            entity_level_code=row["entity_level_code"],
        )
        for row in entity_rows
    )
    forest = [node.to_dict() for node in build_affiliate_forest(entities, tuple(leaves))]
    await _attach_lookup_labels(conn, forest)
    attach_organization_aliases(
        forest,
        aliases,
        entity_id_key="entity_id",
    )
    return forest


def _collect_lookup_codes(nodes: list[dict[str, Any]]) -> list[str]:
    """Every entity-level and person-side code in the forest."""
    codes: list[str] = []
    for node in nodes:
        if node.get("entity_level_code"):
            codes.append(node["entity_level_code"])
        for person in node.get("people", []):
            codes.append(person["person_side_code"])
        codes.extend(_collect_lookup_codes(node.get("children", [])))
    return codes


def _apply_lookup_labels(nodes: list[dict[str, Any]], labels: dict[str, str]) -> None:
    """Write display labels onto the JSON forest, falling back to the code."""
    for node in nodes:
        level = node.get("entity_level_code")
        node["entity_level_label"] = labels.get(level, level) if level else None
        for person in node.get("people", []):
            side = person["person_side_code"]
            person["person_side_label"] = labels.get(side, side)
        _apply_lookup_labels(node.get("children", []), labels)


async def _attach_lookup_labels(conn: asyncpg.Connection, forest: list[dict[str, Any]]) -> None:
    """Hydrate ``entity_level_label`` / ``person_side_label`` from lookup rows."""
    _apply_lookup_labels(forest, await labels_for_codes(conn, _collect_lookup_codes(forest)))


async def fetch_voc_evidence(conn: asyncpg.Connection, post_id: str, voc_type_code: str) -> dict[str, Any]:
    """Lookup label plus extractive excerpts for this post's VOC type."""
    label_row = await conn.fetchrow(
        "select lookup_label from common_lookup_value where lookup_code = $1",
        voc_type_code,
    )
    body_row = await conn.fetchrow("select post_body from source_post where post_id = $1", post_id)
    post_body = "" if body_row is None else body_row["post_body"]
    counterparties = await conn.fetch(
        """
        select c.counterparty_entity_name, c.relationship_type_code, v.lookup_label as relationship_label,
               c.verification_status_code, c.verification_evidence_url
        from post_counterparty_entity c
        join common_lookup_value v on v.lookup_code = c.relationship_type_code
        where c.post_id = $1
        order by c.counterparty_entity_name
        """,
        post_id,
    )
    names: list[str] = [row["counterparty_entity_name"] for row in counterparties]
    for person in await fetch_post_keymen(conn, post_id, organization_aliases=()):
        names.extend(affiliation["organization_name"] for affiliation in person["affiliations"])
    return {
        "post_id": post_id,
        "voc_type_code": voc_type_code,
        "voc_type_label": label_row["lookup_label"] if label_row is not None else voc_type_code,
        "excerpts": list(sentence_excerpts(post_body, names)),
        "counterparties": [
            {
                "counterparty_entity_name": row["counterparty_entity_name"],
                "relationship_type_code": row["relationship_type_code"],
                "relationship_label": row["relationship_label"],
                "evidence_excerpt": first_excerpt_for(post_body, row["counterparty_entity_name"]),
                "verification_status_code": row["verification_status_code"],
                "verification_evidence_url": row["verification_evidence_url"],
            }
            for row in counterparties
        ],
    }
