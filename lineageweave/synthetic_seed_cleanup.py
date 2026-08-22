"""Safely remove only synthetic seed rows after real source ingestion.

The cleanup deliberately never mutates analysis-run tables. A source post that
has entered an immutable snapshot or run-scoped lineage edge is reported as
blocked and left for an explicit operator procedure.
"""

from __future__ import annotations

from typing import Any

from backend.app.post_eligibility import (
    source_context_missing_sql,
    source_context_present_sql,
)


async def cleanup_synthetic_seed(conn: Any, *, apply: bool = False) -> dict[str, int]:
    """Dry-run or apply conservative row-level synthetic cleanup."""
    # Safe SQL: both fragments interpolate only the fixed SOURCE_CONTEXT_COLUMNS identifier list shared with demo_scope; no request-derived value is composed.
    candidates = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post.post_id
          from source_post post
          join corporate_entity entity
            on entity.corporate_entity_id = post.corporate_entity_id
         where {source_context_missing_sql('post')}
           and entity.corporate_entity_code like 'DEMO-%'
           and exists (
               select 1
                 from source_post real_post
                where real_post.corporate_entity_id = post.corporate_entity_id
                  and ({source_context_present_sql('real_post')})
           )
        """
    )
    candidate_ids = [row["post_id"] for row in candidates]
    if not candidate_ids:
        return {
            "candidate_posts": 0,
            "blocked_posts": 0,
            "deletable_posts": 0,
            "deleted_posts": 0,
        }

    blocked = await conn.fetch(
        """
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
        """,
        candidate_ids,
    )
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
        await conn.execute(
            """
            create temporary table if not exists synthetic_cleanup_target_post (
                post_id uuid primary key
            ) on commit drop
            """
        )
        await conn.execute("truncate table pg_temp.synthetic_cleanup_target_post")
        await conn.execute(
            """
            insert into pg_temp.synthetic_cleanup_target_post (post_id)
            select unnest($1::uuid[])
            """,
            deletable_ids,
        )
        # The catalog chooses only single-column, non-cascading foreign keys
        # that reference source_post. Identifier rendering remains inside
        # PostgreSQL's quote-aware format(%I); Python never composes identifiers.
        # Immutable analysis references were excluded above and are never mutated.
        await conn.execute(
            """
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
        )
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
