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

from .post_eligibility import source_context_present_sql


def is_demo_scope(corporate_entity_code: str | None) -> bool:
    """True for `make seed`'s synthetic Demo Corp tree (``DEMO-*`` codes)."""
    return bool(corporate_entity_code) and corporate_entity_code.startswith("DEMO-")


async def has_real_source_context(
    conn: asyncpg.Connection, corporate_entity_ids: list[str]
) -> bool:
    """True when the account can see at least one post carrying real
    source-import evidence, not only the synthetic Demo Corp narrative.

    `make seed` never populates a post's ``source_*`` fields; a real
    PostgreSQL import always does (see ``scripts/import_postgresql_posts.py``).
    """
    return bool(
        await conn.fetchval(
            """
            select exists (
                select 1
                  from source_post
                 where (visibility_code = 'public'
                        or corporate_entity_id = any($1::uuid[]))
                   and ({source_context_sql})
            )
            """.format(source_context_sql=source_context_present_sql("source_post")),
            list(corporate_entity_ids),
        )
    )


async def fetch_demo_corporate_entity_ids(conn: asyncpg.Connection) -> set[str]:
    """Synthetic-only Demo entity ids, excluding shared real-import entities.

    A real import may have reused a historical ``DEMO-*`` entity code. Entity
    code is therefore only a seed hint; row-level ``source_*`` evidence decides
    whether the entity is synthetic-only.
    """
    rows = await conn.fetch(
        """
        select entity.corporate_entity_id
          from corporate_entity entity
         where entity.corporate_entity_code like 'DEMO-%'
           and not exists (
               select 1
                 from source_post real_post
                where real_post.corporate_entity_id = entity.corporate_entity_id
                  and ({source_context_sql})
           )
        """.format(source_context_sql=source_context_present_sql("real_post"))
    )
    return {str(row["corporate_entity_id"]) for row in rows}
