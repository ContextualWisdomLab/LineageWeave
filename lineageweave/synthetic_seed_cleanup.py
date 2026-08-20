"""Safely remove only synthetic seed rows after real source ingestion.

The cleanup deliberately never mutates analysis-run tables. A source post that
has entered an immutable snapshot or run-scoped lineage edge is reported as
blocked and left for an explicit operator procedure.
"""

from __future__ import annotations

from typing import Any


SOURCE_CONTEXT_COLUMNS = (
    "source_author_code",
    "source_author_name",
    "source_company_code",
    "source_company_name",
    "source_process_unit_code",
    "source_process_unit_name",
    "source_sales_pool_code",
    "source_sales_pool_name",
    "source_customer_code",
    "source_customer_name",
    "source_project_code",
    "source_project_name",
)


def _missing_source_context(alias: str = "post") -> str:
    """Return the fixed predicate that identifies absent imported evidence."""
    return " and ".join(
        f"nullif(btrim({alias}.{column}), '') is null" for column in SOURCE_CONTEXT_COLUMNS
    )


def _has_source_context(alias: str = "post") -> str:
    """Return the fixed predicate that identifies present imported evidence."""
    return " or ".join(
        f"nullif(btrim({alias}.{column}), '') is not null" for column in SOURCE_CONTEXT_COLUMNS
    )


_CANDIDATE_POSTS_QUERY = f"""
select post.post_id
  from source_post post
 where ({_missing_source_context()})
   and exists (
       select 1
         from source_post real_post
        where real_post.corporate_entity_id = post.corporate_entity_id
          and ({_has_source_context('real_post')})
   )
"""

_BLOCKED_POSTS_QUERY = """
select distinct post_id
  from (
      select source_post_id as post_id
        from analysis_source_snapshot_member
       where source_post_id = any($1::uuid[])
      union
      select child_post_id as post_id
        from analysis_run_lineage_edge
       where child_post_id = any($1::uuid[])
      union
      select parent_post_id as post_id
        from analysis_run_lineage_edge
       where parent_post_id = any($1::uuid[])
  ) referenced
"""

_CREATE_CLEANUP_TARGET_SQL = """
create temporary table if not exists synthetic_cleanup_target_post (
    post_id uuid primary key
) on commit drop
"""

_CLEAR_CLEANUP_TARGET_SQL = "truncate table pg_temp.synthetic_cleanup_target_post"

_INSERT_CLEANUP_TARGETS_QUERY = """
insert into pg_temp.synthetic_cleanup_target_post (post_id)
select unnest($1::uuid[])
"""

# The catalog decides which single-column non-cascading foreign keys require
# cleanup. Dynamic identifier rendering stays inside PostgreSQL's quote-aware
# format(%I) rather than entering an asyncpg statement from Python. The only
# nullable supporting reference is nulled; immutable analysis references are
# precluded by _BLOCKED_POSTS_QUERY and are never mutated here.
_CLEANUP_REFERENCES_SQL = """
do $cleanup$
declare
    reference_row record;
begin
    for reference_row in
        select child_ns.nspname as child_schema,
               child_table.relname as child_table,
               child_column.attname as child_column
          from pg_constraint constraint_row
          join pg_class parent_table
            on parent_table.oid = constraint_row.confrelid
          join pg_class child_table
            on child_table.oid = constraint_row.conrelid
          join pg_namespace child_ns
            on child_ns.oid = child_table.relnamespace
          join pg_attribute child_column
            on child_column.attrelid = child_table.oid
           and child_column.attnum = constraint_row.conkey[1]
         where parent_table.oid = 'source_post'::regclass
           and constraint_row.contype = 'f'
           and constraint_row.confdeltype <> 'c'
           and array_length(constraint_row.conkey, 1) = 1
    loop
        if reference_row.child_table in (
            'analysis_source_snapshot_member',
            'analysis_run_lineage_edge'
        ) then
            continue;
        end if;

        if reference_row.child_table = 'post_counterparty_entity'
           and reference_row.child_column = 'verification_evidence_post_id' then
            execute format(
                'update %I.%I set %I = null where %I in '
                '(select post_id from pg_temp.synthetic_cleanup_target_post)',
                reference_row.child_schema,
                reference_row.child_table,
                reference_row.child_column,
                reference_row.child_column
            );
        else
            execute format(
                'delete from %I.%I where %I in '
                '(select post_id from pg_temp.synthetic_cleanup_target_post)',
                reference_row.child_schema,
                reference_row.child_table,
                reference_row.child_column
            );
        end if;
    end loop;

    delete from source_post
     where post_id in (
         select post_id from pg_temp.synthetic_cleanup_target_post
     );
end
$cleanup$
"""


async def cleanup_synthetic_seed(conn: Any, *, apply: bool = False) -> dict[str, int]:
    """Dry-run or apply conservative row-level synthetic cleanup."""
    candidates = await conn.fetch(_CANDIDATE_POSTS_QUERY)
    candidate_ids = [row["post_id"] for row in candidates]
    if not candidate_ids:
        return {
            "candidate_posts": 0,
            "blocked_posts": 0,
            "deletable_posts": 0,
            "deleted_posts": 0,
        }

    blocked = await conn.fetch(_BLOCKED_POSTS_QUERY, candidate_ids)
    blocked_ids = {row["post_id"] for row in blocked}
    deletable_ids = [post_id for post_id in candidate_ids if post_id not in blocked_ids]
    if not apply or not deletable_ids:
        return {
            "candidate_posts": len(candidate_ids),
            "blocked_posts": len(blocked_ids),
            "deletable_posts": len(deletable_ids),
            "deleted_posts": 0,
        }

    async with conn.transaction():
        await conn.execute(_CREATE_CLEANUP_TARGET_SQL)
        await conn.execute(_CLEAR_CLEANUP_TARGET_SQL)
        await conn.execute(_INSERT_CLEANUP_TARGETS_QUERY, deletable_ids)
        await conn.execute(_CLEANUP_REFERENCES_SQL)
        await conn.execute(
            """
            delete from account_affiliation affiliation
             using process_unit unit, user_account account
             where affiliation.process_unit_id = unit.process_unit_id
               and affiliation.user_account_id = account.user_account_id
               and unit.process_unit_code like 'DEMO-PU-%'
               and account.external_subject_id like 'demo.%'
               and not exists (
                   select 1 from source_post post
                    where post.process_unit_id = unit.process_unit_id
               )
            """
        )
        await conn.execute(
            """
            delete from process_unit unit
             where unit.process_unit_code like 'DEMO-PU-%'
               and not exists (
                   select 1 from source_post post
                    where post.process_unit_id = unit.process_unit_id
               )
               and not exists (
                   select 1 from account_affiliation affiliation
                    where affiliation.process_unit_id = unit.process_unit_id
               )
            """
        )
        await conn.execute(
            """
            delete from corporate_entity entity
             where entity.corporate_entity_code like 'DEMO-%'
               and not exists (
                   select 1 from source_post post
                    where post.corporate_entity_id = entity.corporate_entity_id
               )
               and not exists (
                   select 1 from process_unit unit
                    where unit.corporate_entity_id = entity.corporate_entity_id
               )
               and not exists (
                   select 1 from account_affiliation affiliation
                    where affiliation.corporate_entity_id = entity.corporate_entity_id
               )
               and not exists (
                   select 1 from corporate_entity child
                    where child.parent_entity_id = entity.corporate_entity_id
               )
            """
        )
    return {
        "candidate_posts": len(candidate_ids),
        "blocked_posts": len(blocked_ids),
        "deletable_posts": len(deletable_ids),
        "deleted_posts": len(deletable_ids),
    }
