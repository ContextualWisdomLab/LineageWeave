"""Runs a `KeymanExtractionClient` over a post and persists the result:
`person` (upserted by name + side -- the schema has no unique constraint
on person_name alone, since two different real people can share a name,
but re-running extraction on the same post should not keep creating
duplicate rows for the same extracted mention), `person_affiliation`
(N:N, matched to a real `corporate_entity` by exact case-insensitive name
where possible), and `post_person_mention`. Finishes by calling
`knowledge_graph.persist_edges_for_post` so the Knowledge Graph edges are
computed from the same write, not a separate manual step.
"""

from __future__ import annotations

import asyncpg

from lineageweave.keyman_extraction import KeymanExtractionClient, PersonMention

from .knowledge_graph import persist_edges_for_post


async def _resolve_corporate_entity_id(conn: asyncpg.Connection, organization_name: str) -> str | None:
    row = await conn.fetchrow(
        "select corporate_entity_id from corporate_entity where lower(entity_name) = lower($1)",
        organization_name,
    )
    return str(row["corporate_entity_id"]) if row is not None else None


async def _upsert_person(conn: asyncpg.Connection, mention: PersonMention) -> str:
    row = await conn.fetchrow(
        "select person_id from cataloged_person where person_name = $1 and person_side_code = $2",
        mention.person_name,
        mention.person_side_code,
    )
    if row is not None:
        return str(row["person_id"])
    row = await conn.fetchrow(
        "insert into cataloged_person (person_name, person_side_code) values ($1, $2) returning person_id",
        mention.person_name,
        mention.person_side_code,
    )
    return str(row["person_id"])


async def ingest_post_keymen(
    conn: asyncpg.Connection,
    client: KeymanExtractionClient,
    post_id: str,
    post_title: str,
    post_body: str,
) -> list[PersonMention]:
    """Extracts, persists, and returns the `PersonMention`s found in one post.

    Raises whatever `client.extract` raises (e.g. a `NullKeymanExtractionClient`
    would raise `RuntimeError`) -- callers should check `client.available`
    first, same discipline as every other pluggable channel in this repo.
    """
    mentions = client.extract(post_title, post_body)

    for mention in mentions:
        person_id = await _upsert_person(conn, mention)
        await conn.execute(
            "insert into post_person_mention (post_id, person_id) values ($1, $2) on conflict do nothing",
            post_id,
            person_id,
        )
        for organization_name in mention.affiliated_organization_names:
            corporate_entity_id = await _resolve_corporate_entity_id(conn, organization_name)
            await conn.execute(
                """
                insert into person_affiliation (person_id, affiliated_organization_name, affiliated_corporate_entity_id)
                values ($1, $2, $3)
                on conflict (person_id, affiliated_organization_name)
                do update set affiliated_corporate_entity_id = excluded.affiliated_corporate_entity_id
                """,
                person_id,
                organization_name,
                corporate_entity_id,
            )

    if mentions:
        await persist_edges_for_post(conn, post_id)

    return mentions
