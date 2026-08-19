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

ANALYSIS_REFERENCE_TABLES = {
    "analysis_source_snapshot_member",
    "analysis_run_lineage_edge",
}

# Columns that are an optional supporting reference to another post, not the
# row's own subject -- e.g. post_counterparty_entity's identity is
# (post_id, counterparty_entity_name); verification_evidence_post_id merely
# cites a corroborating post. Deleting the whole row because that citation
# happens to point at a removed synthetic post would destroy real evidence
# belonging to a kept, real post. Null the reference instead of the row.
NULLABLE_REFERENCE_COLUMNS = {
    ("post_counterparty_entity", "verification_evidence_post_id"),
}


def _missing_source_context(alias: str = "post") -> str:
    return " and ".join(
        f"nullif(btrim({alias}.{column}), '') is null" for column in SOURCE_CONTEXT_COLUMNS
    )


def _has_source_context(alias: str = "post") -> str:
    return " or ".join(
        f"nullif(btrim({alias}.{column}), '') is not null" for column in SOURCE_CONTEXT_COLUMNS
    )


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


async def cleanup_synthetic_seed(conn: Any, *, apply: bool = False) -> dict[str, int]:
    """Dry-run or apply conservative row-level synthetic cleanup."""
    candidates = await conn.fetch(
        f"""
        select post.post_id
          from source_post post
          join corporate_entity entity
            on entity.corporate_entity_id = post.corporate_entity_id
         where entity.corporate_entity_code like 'DEMO-%'
           and ({_missing_source_context()})
           and exists (
               select 1
                 from source_post real_post
                where real_post.corporate_entity_id = post.corporate_entity_id
                  and ({_has_source_context('real_post')})
           )
        """
    )
    candidate_ids = [row["post_id"] for row in candidates]
    if not candidate_ids:
        return {"candidate_posts": 0, "blocked_posts": 0, "deletable_posts": 0, "deleted_posts": 0}

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
        fk_rows = await conn.fetch(
            """
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
            """
        )
        for row in fk_rows:
            if row["child_table"] in ANALYSIS_REFERENCE_TABLES:
                continue
            table = f"{_quote_identifier(row['child_schema'])}.{_quote_identifier(row['child_table'])}"
            column = _quote_identifier(row["child_column"])
            if (row["child_table"], row["child_column"]) in NULLABLE_REFERENCE_COLUMNS:
                await conn.execute(
                    f"update {table} set {column} = null where {column} = any($1::uuid[])",
                    deletable_ids,
                )
                continue
            await conn.execute(
                f"delete from {table} where {column} = any($1::uuid[])",
                deletable_ids,
            )
        await conn.execute("delete from source_post where post_id = any($1::uuid[])", deletable_ids)
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
