"""A single asyncpg connection pool -- direct PostgreSQL access, no ORM, no
file-backed database. Every query in this backend goes through this pool."""

from __future__ import annotations

import asyncpg
from fastapi import Request

from backend.app.operations_dashboard import warm_operations_dashboard_read_statements
from backend.app.voice_taxonomy import warm_voice_taxonomy_read_statements


async def _initialize_connection(connection: asyncpg.Connection) -> None:
    """Load array codecs before the first latency-bounded request."""
    await connection.fetchrow(
        "select array[]::uuid[] as uuid_values, array[]::text[] as text_values"
    )
    await warm_operations_dashboard_read_statements(connection)
    await warm_voice_taxonomy_read_statements(connection)
    await warm_customer_master_read_paths(connection)
    await warm_post_list_read_paths(connection)


async def warm_customer_master_read_paths(connection: asyncpg.Connection) -> None:
    """Warm maintained Customer Master projections before readiness."""
    await connection.fetch(
        """
        select customer_code_key, customer_name_group_key, sum(post_count)::bigint
          from customer_hint_group_read_projection
         where visibility_code = 'public'
         group by customer_code_key, customer_name_group_key
         order by sum(post_count) desc, customer_code_key, customer_name_group_key
         limit 21
        """
    )
    await connection.fetch(
        """
        select author_code, author_account_id, account_display_name,
               sum(post_count)::bigint
          from author_hint_group_read_projection
         where visibility_code = 'public'
         group by author_code, author_account_id, account_display_name
         order by sum(post_count) desc, author_code, author_account_id,
                  account_display_name
         limit 21
        """
    )
    await connection.fetch(
        """
        select counterparty.counterparty_entity_name,
               counterparty.relationship_type_code, count(*)::bigint
          from post_counterparty_entity counterparty
          join dashboard_post_read_projection post
            on post.source_post_id = counterparty.post_id
         where post.visibility_code = 'public' and post.source_context_present
         group by counterparty.counterparty_entity_name,
                  counterparty.relationship_type_code
         order by count(*) desc, counterparty.counterparty_entity_name
         limit 100
        """
    )
    await connection.fetch(
        """
        select post_id
          from customer_master_post_read_projection
         where customer_code_key = '' and customer_name_group_key = ''
         order by created_at desc, post_id desc
         limit 21
        """
    )


async def warm_post_list_read_paths(connection: asyncpg.Connection) -> None:
    """Read the measured Post page indexes before readiness is advertised."""
    active = (
        "(source_draft_code is null or btrim(source_draft_code) = '') and "
        "(source_deleted_flag is null or btrim(source_deleted_flag) = '')"
    )
    source_context = (
        "(nullif(btrim(source_author_code), '') is not null or "
        "nullif(btrim(source_author_name), '') is not null or "
        "nullif(btrim(source_company_code), '') is not null or "
        "nullif(btrim(source_company_name), '') is not null or "
        "nullif(btrim(source_process_unit_code), '') is not null or "
        "nullif(btrim(source_process_unit_name), '') is not null or "
        "nullif(btrim(source_sales_pool_code), '') is not null or "
        "nullif(btrim(source_sales_pool_name), '') is not null or "
        "nullif(btrim(source_customer_code), '') is not null or "
        "nullif(btrim(source_customer_name), '') is not null or "
        "nullif(btrim(source_project_code), '') is not null or "
        "nullif(btrim(source_project_name), '') is not null)"
    )
    # Safe SQL: both predicates above are closed schema constants.
    for ordering in (
        "created_at desc, post_id desc",
        "lower(coalesce(post_title, '')), created_at desc, post_id desc",
    ):
        await connection.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            "select post_id from source_post where "
            f"{active} and {source_context} order by {ordering} limit 50"
        )
    await connection.fetch(
        "select projection.post_id, projection.post_body_excerpt, "
        "voice.voice_type_code from post_list_read_projection projection "
        "left join source_post_voice voice on voice.post_id = projection.post_id "
        "and voice.effective_to is null order by projection.post_id limit 50"
    )


async def _reset_connection(connection: asyncpg.Connection) -> None:
    """Reset request state and restore the measured generic-plan policy."""
    await connection.reset()
    await connection.execute("set plan_cache_mode = 'force_generic_plan'")


async def create_pool(database_url: str) -> asyncpg.Pool:
    """Open the process-wide asyncpg pool against ``database_url``."""
    return await asyncpg.create_pool(
        database_url,
        min_size=10,
        max_size=10,
        max_cacheable_statement_size=0,
        server_settings={"jit": "off", "plan_cache_mode": "force_generic_plan"},
        init=_initialize_connection,
        reset=_reset_connection,
    )


def get_pool(request: Request) -> asyncpg.Pool:
    """FastAPI dependency: the pool stored on ``app.state`` at startup."""
    return request.app.state.pool
