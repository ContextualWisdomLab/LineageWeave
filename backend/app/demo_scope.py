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
                   and (
                        nullif(btrim(source_author_code), '') is not null
                        or nullif(btrim(source_author_name), '') is not null
                        or nullif(btrim(source_company_code), '') is not null
                        or nullif(btrim(source_company_name), '') is not null
                        or nullif(btrim(source_process_unit_code), '') is not null
                        or nullif(btrim(source_process_unit_name), '') is not null
                        or nullif(btrim(source_sales_pool_code), '') is not null
                        or nullif(btrim(source_sales_pool_name), '') is not null
                        or nullif(btrim(source_customer_code), '') is not null
                        or nullif(btrim(source_customer_name), '') is not null
                        or nullif(btrim(source_project_code), '') is not null
                        or nullif(btrim(source_project_name), '') is not null
                   )
            )
            """,
            list(corporate_entity_ids),
        )
    )


async def fetch_demo_corporate_entity_ids(conn: asyncpg.Connection) -> set[str]:
    """The `make seed` Demo Corp tree's corporate_entity_ids.

    Small, cacheable-by-caller lookup, not an ABAC gate on its own -- callers
    still apply `has_real_source_context` before treating a row as hideable.
    """
    rows = await conn.fetch(
        "select corporate_entity_id from corporate_entity where corporate_entity_code like 'DEMO-%'"
    )
    return {str(row["corporate_entity_id"]) for row in rows}
