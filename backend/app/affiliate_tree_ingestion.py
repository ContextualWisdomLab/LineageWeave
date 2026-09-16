"""Load a post's Keyman affiliations into the affiliate-tree forest."""

from __future__ import annotations

from typing import Any

import asyncpg

from lineageweave.affiliate_tree import (
    AffiliationLeaf,
    CorporateEntityRow,
    build_affiliate_forest,
)
from lineageweave.organization_alias import attach_organization_aliases
from lineageweave.voc_evidence import first_excerpt_for, sentence_excerpts

from .knowledge_graph import fetch_post_keymen, labels_for_codes
from .organization_name_resolution_ingestion import (
    fetch_corroborated_organization_aliases,
)


async def fetch_affiliate_forest(
    database_connection: asyncpg.Connection,
    post_id: str,
) -> list[dict[str, Any]]:
    """Ancestor forest of every organization this post's Keymen touch."""
    organization_aliases = await fetch_corroborated_organization_aliases(
        database_connection
    )
    corporate_entity_rows = await database_connection.fetch(
        """
        select corporate_entity_id, parent_entity_id, entity_name, entity_level_code
        from corporate_entity
        """
    )
    corporate_entities = tuple(
        CorporateEntityRow(
            entity_id=str(corporate_entity_row["corporate_entity_id"]),
            parent_entity_id=(
                str(corporate_entity_row["parent_entity_id"])
                if corporate_entity_row["parent_entity_id"] is not None
                else None
            ),
            entity_name=corporate_entity_row["entity_name"],
            entity_level_code=corporate_entity_row["entity_level_code"],
        )
        for corporate_entity_row in corporate_entity_rows
    )
    affiliation_leaves: list[AffiliationLeaf] = []
    for post_keyman in await fetch_post_keymen(
        database_connection,
        post_id,
        organization_aliases=organization_aliases,
    ):
        for person_affiliation in post_keyman["affiliations"]:
            affiliation_leaves.append(
                AffiliationLeaf(
                    person_id=post_keyman["person_id"],
                    person_name=post_keyman["person_name"],
                    person_side_code=post_keyman["person_side_code"],
                    organization_name=person_affiliation["organization_name"],
                    corporate_entity_id=person_affiliation["corporate_entity_id"],
                )
            )
    affiliate_forest = [
        affiliate_node.to_dict()
        for affiliate_node in build_affiliate_forest(
            corporate_entities,
            tuple(affiliation_leaves),
        )
    ]
    await _attach_lookup_labels(database_connection, affiliate_forest)
    attach_organization_aliases(
        affiliate_forest,
        organization_aliases,
        entity_id_key="entity_id",
    )
    return affiliate_forest


def _collect_lookup_codes(affiliate_nodes: list[dict[str, Any]]) -> list[str]:
    """Every entity-level and person-side code in the forest."""
    lookup_codes: list[str] = []
    for affiliate_node in affiliate_nodes:
        if affiliate_node.get("entity_level_code"):
            lookup_codes.append(affiliate_node["entity_level_code"])
        for affiliated_person in affiliate_node.get("people", []):
            lookup_codes.append(affiliated_person["person_side_code"])
        lookup_codes.extend(_collect_lookup_codes(affiliate_node.get("children", [])))
    return lookup_codes


def _apply_lookup_labels(
    affiliate_nodes: list[dict[str, Any]],
    lookup_labels: dict[str, str],
) -> None:
    """Write display labels onto the JSON forest, falling back to the code."""
    for affiliate_node in affiliate_nodes:
        entity_level_code = affiliate_node.get("entity_level_code")
        affiliate_node["entity_level_label"] = (
            lookup_labels.get(entity_level_code, entity_level_code)
            if entity_level_code
            else None
        )
        for affiliated_person in affiliate_node.get("people", []):
            person_side_code = affiliated_person["person_side_code"]
            affiliated_person["person_side_label"] = lookup_labels.get(
                person_side_code,
                person_side_code,
            )
        _apply_lookup_labels(affiliate_node.get("children", []), lookup_labels)


async def _attach_lookup_labels(
    database_connection: asyncpg.Connection,
    affiliate_forest: list[dict[str, Any]],
) -> None:
    """Hydrate ``entity_level_label`` / ``person_side_label`` from lookup rows."""
    _apply_lookup_labels(
        affiliate_forest,
        await labels_for_codes(
            database_connection,
            _collect_lookup_codes(affiliate_forest),
        ),
    )


async def fetch_voc_evidence(
    database_connection: asyncpg.Connection,
    post_id: str,
    voc_type_code: str,
) -> dict[str, Any]:
    """Lookup label plus extractive excerpts for this post's VOC type."""
    voc_label_row = await database_connection.fetchrow(
        "select lookup_label from common_lookup_value where lookup_code = $1",
        voc_type_code,
    )
    source_post_body_row = await database_connection.fetchrow(
        "select post_body from source_post where post_id = $1",
        post_id,
    )
    post_body = (
        "" if source_post_body_row is None else source_post_body_row["post_body"]
    )
    counterparty_rows = await database_connection.fetch(
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
    evidence_organization_names: list[str] = [
        counterparty_row["counterparty_entity_name"]
        for counterparty_row in counterparty_rows
    ]
    for post_keyman in await fetch_post_keymen(
        database_connection,
        post_id,
        organization_aliases=(),
    ):
        evidence_organization_names.extend(
            person_affiliation["organization_name"]
            for person_affiliation in post_keyman["affiliations"]
        )
    return {
        "post_id": post_id,
        "voc_type_code": voc_type_code,
        "voc_type_label": voc_label_row["lookup_label"]
        if voc_label_row is not None
        else voc_type_code,
        "excerpts": list(sentence_excerpts(post_body, evidence_organization_names)),
        "counterparties": [
            {
                "counterparty_entity_name": counterparty_row[
                    "counterparty_entity_name"
                ],
                "relationship_type_code": counterparty_row["relationship_type_code"],
                "relationship_label": counterparty_row["relationship_label"],
                "evidence_excerpt": first_excerpt_for(
                    post_body,
                    counterparty_row["counterparty_entity_name"],
                ),
                "verification_status_code": counterparty_row[
                    "verification_status_code"
                ],
                "verification_evidence_url": counterparty_row[
                    "verification_evidence_url"
                ],
            }
            for counterparty_row in counterparty_rows
        ],
    }
