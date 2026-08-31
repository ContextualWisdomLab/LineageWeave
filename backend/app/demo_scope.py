"""Shared demo-vs-real scope helpers (ADR 0001 / ADR 0042).

`make seed`'s Demo Corp narrative exists so a fresh, dataless install has
something to show. Once an account can see at least one post carrying real
source-import evidence, the synthetic Demo Corp tree is no longer needed to
fill an empty screen and must stop appearing next to real evidence -- a
buyer must never mistake a fabricated contact (e.g. Ada West, Priya Nair)
for a real one.
"""

from __future__ import annotations

import asyncpg


def is_demo_scope(corporate_entity_code: str | None) -> bool:
    """True for `make seed`'s synthetic Demo Corp tree (``DEMO-*`` codes)."""
    return bool(corporate_entity_code) and corporate_entity_code.startswith("DEMO-")


async def has_real_source_context(
    conn: asyncpg.Connection, corporate_entity_ids: list[str]
) -> bool:
    """Return whether the account can see imported source evidence."""
    return bool(
        # Safe SQL: this is immutable schema text; authorized entity ids are bound through $1.
        await conn.fetchval(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            """
            select exists (
                select 1
                  from dashboard_post_read_projection source_post
                 where (visibility_code = 'public'
                        or corporate_entity_id = any($1::uuid[]))
                   and source_context_present
            )
            """,
            list(corporate_entity_ids),
        )
    )


async def fetch_demo_corporate_entity_ids(conn: asyncpg.Connection) -> set[str]:
    """Return synthetic-only Demo entity IDs, excluding imported entities."""
    rows = await conn.fetch(
        """
        select entity.corporate_entity_id
          from corporate_entity entity
         where entity.corporate_entity_code like 'DEMO-%'
           and not exists (
               select 1
                 from dashboard_post_read_projection real_post
                where real_post.corporate_entity_id = entity.corporate_entity_id
                  and real_post.source_context_present
           )
        """
    )
    return {str(row["corporate_entity_id"]) for row in rows}
