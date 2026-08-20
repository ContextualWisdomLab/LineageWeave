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


_HAS_REAL_SOURCE_CONTEXT_QUERY = """
select exists (
    select 1
      from source_post
     where (visibility_code = 'public'
            or corporate_entity_id = any($1::uuid[]))
       and ({source_context_sql})
)
""".format(source_context_sql=source_context_present_sql("source_post"))

_FETCH_DEMO_CORPORATE_ENTITY_IDS_QUERY = """
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


def is_demo_scope(corporate_entity_code: str | None) -> bool:
    """True for `make seed`'s synthetic Demo Corp tree (``DEMO-*`` codes)."""
    return bool(corporate_entity_code) and corporate_entity_code.startswith("DEMO-")


async def has_real_source_context(
    conn: asyncpg.Connection, corporate_entity_ids: list[str]
) -> bool:
    """Return whether the account can see imported source evidence."""
    return bool(
        await conn.fetchval(
            _HAS_REAL_SOURCE_CONTEXT_QUERY,
            list(corporate_entity_ids),
        )
    )


async def fetch_demo_corporate_entity_ids(conn: asyncpg.Connection) -> set[str]:
    """Return synthetic-only Demo entity IDs, excluding imported entities."""
    rows = await conn.fetch(_FETCH_DEMO_CORPORATE_ENTITY_IDS_QUERY)
    return {str(row["corporate_entity_id"]) for row in rows}
