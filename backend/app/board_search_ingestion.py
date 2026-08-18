"""Load authorized 게시판 search facts and bind them through the ontology."""

from __future__ import annotations

from typing import Any

import asyncpg

from lineageweave.board_search import (
    SEARCH_EMPTY_NEXT_ACTION,
    classify_board_query,
    post_matches_bind,
)


async def search_authorized_board(
    conn: asyncpg.Connection,
    query: str,
    can_see_post: Any,
    serialize_post: Any,
    lookup_labels: Any,
) -> dict[str, object]:
    """Return ontology-bound posts. Unbound queries stay empty."""
    post_rows = await conn.fetch(
        "select post_id, post_title, voc_type_code, visibility_code, "
        "corporate_entity_id, created_at from source_post order by created_at desc"
    )
    visible = [row for row in post_rows if can_see_post(row)]
    visible_ids = [row["post_id"] for row in visible]
    person_rows = await conn.fetch(
        """
        select ppm.post_id, p.person_name
        from post_person_mention ppm
        join cataloged_person p on p.person_id = ppm.person_id
        where ppm.post_id = any($1::uuid[])
        """,
        visible_ids,
    ) if visible_ids else []
    team_rows = await conn.fetch(
        """
        select ptm.post_id, t.team_name
        from post_team_mention ptm
        join cataloged_team t on t.team_id = ptm.team_id
        where ptm.post_id = any($1::uuid[])
        """,
        visible_ids,
    ) if visible_ids else []
    org_rows = await conn.fetch(
        """
        select pce.post_id, pce.counterparty_entity_name as org_name,
               pce.relationship_type_code
        from post_counterparty_entity pce
        where pce.post_id = any($1::uuid[])
        """,
        visible_ids,
    ) if visible_ids else []
    corp_rows = await conn.fetch(
        """
        select sp.post_id, ce.entity_name as org_name
        from source_post sp
        join corporate_entity ce on ce.corporate_entity_id = sp.corporate_entity_id
        where sp.post_id = any($1::uuid[])
        """,
        visible_ids,
    ) if visible_ids else []
    people_by_post: dict[str, list[str]] = {}
    orgs_by_post: dict[str, list[str]] = {}
    teams_by_post: dict[str, list[str]] = {}
    rels_by_post: dict[str, list[str]] = {}
    all_people: list[str] = []
    all_orgs: list[str] = []
    all_teams: list[str] = []
    for row in person_rows:
        people_by_post.setdefault(str(row["post_id"]), []).append(row["person_name"])
        all_people.append(row["person_name"])
    for row in team_rows:
        teams_by_post.setdefault(str(row["post_id"]), []).append(row["team_name"])
        all_teams.append(row["team_name"])
    for row in org_rows:
        orgs_by_post.setdefault(str(row["post_id"]), []).append(row["org_name"])
        all_orgs.append(row["org_name"])
        rels_by_post.setdefault(str(row["post_id"]), []).append(row["relationship_type_code"])
    for row in corp_rows:
        orgs_by_post.setdefault(str(row["post_id"]), []).append(row["org_name"])
        all_orgs.append(row["org_name"])
    bind = classify_board_query(
        query,
        person_names=all_people,
        organization_names=all_orgs,
        team_names=all_teams,
    )
    if bind is None:
        return {
            "query": query.strip(),
            "grounded": False,
            "bind": None,
            "posts": [],
            "empty_next_action": SEARCH_EMPTY_NEXT_ACTION,
        }
    matched = [
        row
        for row in visible
        if post_matches_bind(
            bind,
            voc_type_code=row["voc_type_code"],
            person_names=people_by_post.get(str(row["post_id"]), []),
            organization_names=orgs_by_post.get(str(row["post_id"]), []),
            team_names=teams_by_post.get(str(row["post_id"]), []),
            relationship_codes=rels_by_post.get(str(row["post_id"]), []),
            has_keyman=bool(people_by_post.get(str(row["post_id"]))),
        )
    ]
    labels = await lookup_labels(conn, matched) if matched else {}
    return {
        "query": query.strip(),
        "grounded": True,
        "bind": bind,
        "posts": [serialize_post(row, labels) for row in matched],
        "empty_next_action": None if matched else SEARCH_EMPTY_NEXT_ACTION,
    }
