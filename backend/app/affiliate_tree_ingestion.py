"""Load a post's Keyman affiliations into the affiliate-tree forest."""

from __future__ import annotations

from typing import Any

import asyncpg

from lineageweave.affiliate_tree import AffiliationLeaf, CorporateEntityRow, build_affiliate_forest
from lineageweave.voc_evidence import first_excerpt_for, sentence_excerpts

from .knowledge_graph import fetch_post_keymen


async def fetch_affiliate_forest(conn: asyncpg.Connection, post_id: str) -> list[dict[str, Any]]:
    """Ancestor forest of every organization this post's Keymen touch."""
    entity_rows = await conn.fetch(
        """
        select corporate_entity_id, parent_entity_id, entity_name, entity_level_code
        from corporate_entity
        """
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
    leaves: list[AffiliationLeaf] = []
    for person in await fetch_post_keymen(conn, post_id):
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
    return [node.to_dict() for node in build_affiliate_forest(entities, tuple(leaves))]


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
        select c.counterparty_entity_name, c.relationship_type_code, v.lookup_label as relationship_label
        from post_counterparty_entity c
        join common_lookup_value v on v.lookup_code = c.relationship_type_code
        where c.post_id = $1
        order by c.counterparty_entity_name
        """,
        post_id,
    )
    names: list[str] = [row["counterparty_entity_name"] for row in counterparties]
    for person in await fetch_post_keymen(conn, post_id):
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
            }
            for row in counterparties
        ],
    }
