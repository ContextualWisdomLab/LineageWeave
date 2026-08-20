#!/usr/bin/env python3
"""Apply the reviewed GREEN repair for static asyncpg statement contracts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    """Read one UTF-8 repository file."""

    return (ROOT / relative_path).read_text(encoding="utf-8")


def _write(relative_path: str, content: str) -> None:
    """Write one UTF-8 repository file, creating its parent directory."""

    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _replace_once(relative_path: str, old: str, new: str) -> None:
    """Replace one exact source fragment and fail if the parent moved."""

    content = _read(relative_path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(
            f"expected one replacement in {relative_path}, found {count}: {old[:80]!r}"
        )
    _write(relative_path, content.replace(old, new, 1))


def _insert_after(relative_path: str, marker: str, addition: str) -> None:
    """Insert one exact block after a stable marker."""

    content = _read(relative_path)
    if addition.strip() in content:
        raise RuntimeError(f"addition already present in {relative_path}")
    count = content.count(marker)
    if count != 1:
        raise RuntimeError(f"expected one marker in {relative_path}, found {count}")
    _write(relative_path, content.replace(marker, marker + addition, 1))


def _replace_between(
    relative_path: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> None:
    """Replace one inclusive marker-delimited source region."""

    content = _read(relative_path)
    start = content.find(start_marker)
    if start < 0:
        raise RuntimeError(f"start marker not found in {relative_path}")
    end_start = content.find(end_marker, start)
    if end_start < 0:
        raise RuntimeError(f"end marker not found in {relative_path}")
    end = end_start + len(end_marker)
    _write(relative_path, content[:start] + replacement + content[end:])


def _write_catalog_sql_helper() -> None:
    """Create the single audited boundary for catalog-derived identifiers."""

    _write(
        "lineageweave/catalog_sql.py",
        '''"""Audited SQL composition for PostgreSQL catalog-derived identifiers.

Only identifiers read from PostgreSQL's own catalog enter this boundary. Values
remain asyncpg parameters; identifiers are quoted according to PostgreSQL rules.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def quote_catalog_identifier(value: str) -> str:
    """Quote one non-empty PostgreSQL identifier and reject NUL characters."""

    if not value or "\\x00" in value:
        raise ValueError("catalog identifier must be non-empty and contain no NUL")
    return '"' + value.replace('"', '""') + '"'


def catalog_reference_cleanup_sql(
    schema_name: str,
    table_name: str,
    column_name: str,
    *,
    nullify: bool,
) -> str:
    """Build one value-parameterized cleanup statement from quoted identifiers."""

    table = (
        f"{quote_catalog_identifier(schema_name)}."
        f"{quote_catalog_identifier(table_name)}"
    )
    column = quote_catalog_identifier(column_name)
    if nullify:
        return f"update {table} set {column} = null where {column} = any($1::uuid[])"
    return f"delete from {table} where {column} = any($1::uuid[])"


async def execute_catalog_reference_cleanup(
    conn: Any,
    *,
    schema_name: str,
    table_name: str,
    column_name: str,
    referenced_ids: Sequence[Any],
    nullify: bool,
) -> None:
    """Execute one audited catalog-reference cleanup with bound UUID values."""

    statement = catalog_reference_cleanup_sql(
        schema_name,
        table_name,
        column_name,
        nullify=nullify,
    )
    await conn.execute(statement, list(referenced_ids))
''',
    )
    _write(
        "tests/test_catalog_sql.py",
        '''"""Security and branch contracts for catalog-derived SQL identifiers."""

from __future__ import annotations

import asyncio

import pytest

from lineageweave.catalog_sql import (
    catalog_reference_cleanup_sql,
    execute_catalog_reference_cleanup,
    quote_catalog_identifier,
)


def test_catalog_identifier_quotes_embedded_double_quotes() -> None:
    """Catalog names cannot escape the quoted-identifier boundary."""

    assert quote_catalog_identifier('odd"name') == '"odd""name"'
    with pytest.raises(ValueError):
        quote_catalog_identifier("")
    with pytest.raises(ValueError):
        quote_catalog_identifier("bad\\x00name")


def test_catalog_cleanup_statements_keep_values_parameterized() -> None:
    """Both cleanup modes quote identifiers and retain the UUID placeholder."""

    delete_sql = catalog_reference_cleanup_sql(
        "public", 'child"table', "post_id", nullify=False
    )
    update_sql = catalog_reference_cleanup_sql(
        "audit", "evidence", 'source"post', nullify=True
    )

    assert delete_sql == (
        'delete from "public"."child""table" '
        'where "post_id" = any($1::uuid[])'
    )
    assert update_sql == (
        'update "audit"."evidence" set "source""post" = null '
        'where "source""post" = any($1::uuid[])'
    )


def test_catalog_cleanup_executes_only_the_composed_statement() -> None:
    """The executor passes quoted SQL and UUID values as separate arguments."""

    class FakeConnection:
        def __init__(self) -> None:
            self.calls: list[tuple[str, list[str]]] = []

        async def execute(self, statement: str, identifiers: list[str]) -> None:
            self.calls.append((statement, identifiers))

    connection = FakeConnection()
    asyncio.run(
        execute_catalog_reference_cleanup(
            connection,
            schema_name="public",
            table_name="child_table",
            column_name="post_id",
            referenced_ids=["post-1"],
            nullify=False,
        )
    )

    assert connection.calls == [
        (
            'delete from "public"."child_table" '
            'where "post_id" = any($1::uuid[])',
            ["post-1"],
        )
    ]
''',
    )


def _repair_customer_hint_ingestion() -> None:
    path = "backend/app/customer_hint_ingestion.py"
    constant = '''\n_CUSTOMER_HINT_EVIDENCE_SQL = f"""\nselect post_title, left(post_body, {_RAW_BODY_SQL_CAP}) as post_body\n  from source_post\n where source_customer_code = $1\n   and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post")}\n order by created_at desc\n limit {_SAMPLE_POST_LIMIT}\n"""\n'''
    _insert_after(path, "_RAW_BODY_SQL_CAP = 20000\n", constant)
    _replace_between(
        path,
        "    # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli -- The eligibility clause is schema-fixed; hint_code is bound through $1.\n",
        "        hint_code,\n    )",
        "    rows = await conn.fetch(_CUSTOMER_HINT_EVIDENCE_SQL, hint_code)",
    )
    _replace_once(
        path,
        "        # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli -- The generated code is a bound value, not part of the SQL statement.\n",
        "",
    )


def _repair_demo_scope() -> None:
    path = "backend/app/demo_scope.py"
    constants = '''\n_HAS_REAL_SOURCE_CONTEXT_SQL = """\nselect exists (\n    select 1\n      from source_post\n     where (visibility_code = 'public'\n            or corporate_entity_id = any($1::uuid[]))\n       and ({source_context_sql})\n)\n""".format(source_context_sql=source_context_present_sql("source_post"))\n\n_FETCH_DEMO_CORPORATE_ENTITY_IDS_SQL = """\nselect entity.corporate_entity_id\n  from corporate_entity entity\n where entity.corporate_entity_code like 'DEMO-%'\n   and not exists (\n       select 1\n         from source_post real_post\n        where real_post.corporate_entity_id = entity.corporate_entity_id\n          and ({source_context_sql})\n   )\n""".format(source_context_sql=source_context_present_sql("real_post"))\n'''
    _insert_after(path, "from .post_eligibility import source_context_present_sql\n", constants)
    _replace_between(
        path,
        "    return bool(\n        # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli -- Only the fixed source_* column predicate is composed; account IDs remain an asyncpg parameter.\n",
        "            list(corporate_entity_ids),\n        )\n    )",
        '''    return bool(
        await conn.fetchval(
            _HAS_REAL_SOURCE_CONTEXT_SQL,
            list(corporate_entity_ids),
        )
    )''',
    )
    _replace_between(
        path,
        "    # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli -- Only the fixed source_* column predicate is composed; entity IDs are not interpolated into SQL.\n",
        "    )\n    return {str(row[\"corporate_entity_id\"]) for row in rows}",
        '''    rows = await conn.fetch(_FETCH_DEMO_CORPORATE_ENTITY_IDS_SQL)
    return {str(row["corporate_entity_id"]) for row in rows}''',
    )


def _repair_entity_relationship_ingestion() -> None:
    path = "backend/app/entity_relationship_ingestion.py"
    constant = '''\n_RELATIONSHIP_NETWORK_SQL = f"""\nwith scoped as (\n    select counterparty.counterparty_entity_name,\n           counterparty.relationship_type_code,\n           lookup.lookup_label as relationship_label\n      from post_counterparty_entity counterparty\n      join source_post post on post.post_id = counterparty.post_id\n      join common_lookup_value lookup\n        on lookup.lookup_code = counterparty.relationship_type_code\n     where (post.visibility_code = 'public' or post.corporate_entity_id = any($1::uuid[]))\n       and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}\n), grouped as (\n    select counterparty_entity_name, relationship_type_code, relationship_label,\n           count(*) as post_count\n      from scoped\n     group by counterparty_entity_name, relationship_type_code, relationship_label\n), entity_totals as (\n    select counterparty_entity_name, sum(post_count) as total_post_count\n      from grouped\n     group by counterparty_entity_name\n), top_entities as materialized (\n    select counterparty_entity_name, total_post_count\n      from entity_totals\n     order by total_post_count desc, counterparty_entity_name\n     limit {_RELATIONSHIP_NETWORK_LIMIT}\n)\nselect top_entities.counterparty_entity_name, top_entities.total_post_count,\n       json_agg(\n           json_build_object(\n               'relationship_type_code', grouped.relationship_type_code,\n               'relationship_label', grouped.relationship_label,\n               'post_count', grouped.post_count\n           )\n           order by grouped.post_count desc, grouped.relationship_type_code\n       ) as relationships\n  from top_entities\n  join grouped on grouped.counterparty_entity_name = top_entities.counterparty_entity_name\n group by top_entities.counterparty_entity_name, top_entities.total_post_count\n order by top_entities.total_post_count desc, top_entities.counterparty_entity_name\n"""\n'''
    _insert_after(path, "_RELATIONSHIP_NETWORK_LIMIT = 100\n", constant)
    _replace_between(
        path,
        "    # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli -- Only the fixed source_* predicate and bounded network limit are composed; entity IDs are $1.\n",
        "        list(corporate_entity_ids),\n    )",
        '''    rows = await conn.fetch(
        _RELATIONSHIP_NETWORK_SQL,
        list(corporate_entity_ids),
    )''',
    )


def _repair_synthetic_seed_cleanup() -> None:
    path = "lineageweave/synthetic_seed_cleanup.py"
    _insert_after(
        path,
        "from typing import Any\n",
        "\nfrom .catalog_sql import execute_catalog_reference_cleanup\n",
    )
    constant = '''\n_SYNTHETIC_CANDIDATE_SQL = f"""\nselect post.post_id\n  from source_post post\n where ({_missing_source_context()})\n   and exists (\n       select 1\n         from source_post real_post\n        where real_post.corporate_entity_id = post.corporate_entity_id\n          and ({_has_source_context('real_post')})\n   )\n"""\n\n'''
    _insert_after(
        path,
        '''def _has_source_context(alias: str = "post") -> str:
    return " or ".join(
        f"nullif(btrim({alias}.{column}), '') is not null" for column in SOURCE_CONTEXT_COLUMNS
    )

''',
        constant,
    )
    _replace_once(
        path,
        '''def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


''',
        "",
    )
    _replace_between(
        path,
        "    candidates = await conn.fetch(\n        f\"\"\"\n",
        "        \"\"\"\n    )",
        "    candidates = await conn.fetch(_SYNTHETIC_CANDIDATE_SQL)",
    )
    _replace_between(
        path,
        "            table = f\"{_quote_identifier(row['child_schema'])}.{_quote_identifier(row['child_table'])}\"\n",
        "                deletable_ids,\n            )",
        '''            await execute_catalog_reference_cleanup(
                conn,
                schema_name=row["child_schema"],
                table_name=row["child_table"],
                column_name=row["child_column"],
                referenced_ids=deletable_ids,
                nullify=(
                    row["child_table"], row["child_column"]
                ) in NULLABLE_REFERENCE_COLUMNS,
            )''',
    )


def _repair_backfill_post_content() -> None:
    path = "scripts/backfill_post_content.py"
    constant = '''\n_SELECT_POSTS_SQL = f"""\nselect post.post_id\n  from source_post post\n where {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}\n   and (\n       ($1::uuid[] is not null and post.post_id = any($1::uuid[]))\n       or (\n           $1::uuid[] is null\n           and (\n               (\n                   $2::boolean\n                   and not exists (\n                       select 1 from post_content_unit unit\n                        where unit.post_id = post.post_id\n                   )\n               )\n               or (\n                   not $2::boolean\n                   and (\n                       not exists (\n                           select 1 from post_content_unit unit\n                            where unit.post_id = post.post_id\n                       )\n                       or exists (\n                           select 1\n                             from post_content_unit unit\n                             left join post_content_embedding embedding\n                               on embedding.post_content_unit_id = unit.post_content_unit_id\n                            where unit.post_id = post.post_id\n                              and embedding.post_content_unit_id is null\n                       )\n                   )\n               )\n           )\n       )\n   )\n order by post.created_at, post.post_id\n limit coalesce($3::bigint, 9223372036854775807)\n"""\n'''
    _insert_after(
        path,
        "from lineageweave.post_structure import ContextualOrchestratorPostStructureClient, NullPostStructureClient\n",
        constant,
    )
    _replace_between(
        path,
        "        conditions = [SOURCE_POST_ELIGIBILITY_SQL.format(alias=\"post\")]\n",
        "            *query_args,\n        )",
        '''        selected_rows = await conn.fetch(
            _SELECT_POSTS_SQL,
            post_ids or None,
            normalize_only,
            limit,
        )''',
    )


def _repair_backfill_post_keymen() -> None:
    path = "scripts/backfill_post_keymen.py"
    constants = '''\n_SELECT_POST_BY_ID_SQL = f"""\nselect post_id, post_title, post_body, author_account_id,\n       source_author_code, source_company_code,\n       source_customer_code, source_project_code,\n       source_sales_pool_code, source_process_unit_code\n  from source_post post\n where post.post_id = $1\n   and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}\n"""\n\n_SELECT_UNMENTIONED_POSTS_SQL = f"""\nselect post_id, post_title, post_body, author_account_id,\n       source_author_code, source_company_code,\n       source_customer_code, source_project_code,\n       source_sales_pool_code, source_process_unit_code\n  from source_post post\n where {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}\n   and not exists (\n       select 1 from post_person_mention mention\n        where mention.post_id = post.post_id\n   )\n order by post.created_at, post.post_id\n limit $1\n"""\n'''
    _insert_after(
        path,
        "from lineageweave.post_content_normalization import normalize_post_body\n",
        constants,
    )
    _replace_between(
        path,
        "    eligibility = SOURCE_POST_ELIGIBILITY_SQL.format(alias=\"post\")\n",
        "    )\n\n\nasync def _run",
        '''    if post_id:
        return list(await conn.fetch(_SELECT_POST_BY_ID_SQL, post_id))
    return list(await conn.fetch(_SELECT_UNMENTIONED_POSTS_SQL, limit))


async def _run''',
    )


def _repair_backfill_post_summaries() -> None:
    path = "scripts/backfill_post_summaries.py"
    constant = '''\n_LOAD_POSTS_SQL = f"""\nselect post.post_id, post.post_title, post.post_body, post.author_account_id,\n       author.display_name as author_name,\n       post.source_author_code, post.source_author_name,\n       post.source_company_code, post.source_company_name,\n       post.source_process_unit_code, post.source_process_unit_name,\n       post.source_sales_pool_code, post.source_sales_pool_name,\n       post.source_customer_code, post.source_customer_name,\n       post.source_project_code, post.source_project_name,\n       post.secondary_grouping_key as project_field,\n       customer.entity_name as customer_name,\n       coalesce(\n           (select array_agg(distinct affiliated.entity_name)\n              from account_affiliation affiliation\n              join corporate_entity affiliated\n                on affiliated.corporate_entity_id = affiliation.corporate_entity_id\n             where affiliation.user_account_id = post.author_account_id),\n           '{{}}'::text[]\n       ) as author_affiliations\n  from source_post post\n  left join user_account author\n    on author.user_account_id = post.author_account_id\n  left join corporate_entity customer\n    on customer.corporate_entity_id = post.corporate_entity_id\n where {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}\n   and (\n       ($1::uuid[] is not null and post.post_id = any($1::uuid[]))\n       or (\n           $1::uuid[] is null\n           and nullif(btrim(post.source_project_code::text), '') is null\n           and nullif(btrim(post.source_project_name::text), '') is null\n           and not exists (\n               select 1 from post_project_mention mention\n                where mention.post_id = post.post_id\n           )\n       )\n   )\n order by post.created_at, post.post_id\n limit coalesce($2::bigint, 9223372036854775807)\n"""\n'''
    _insert_after(
        path,
        "from lineageweave.semantic_hints import format_semantic_hints\n",
        constant,
    )
    _replace_between(
        path,
        "    conditions = [SOURCE_POST_ELIGIBILITY_SQL.format(alias=\"post\")]\n",
        "        *args,\n    )",
        '''    return await conn.fetch(
        _LOAD_POSTS_SQL,
        post_ids or None,
        limit,
    )''',
    )


def _repair_protocol_stub() -> None:
    _replace_once(
        "lineageweave/post_structure.py",
        ''') -> tuple[StructureDecision, ...]: ...


class NullPostStructureClient:''',
        ''') -> tuple[StructureDecision, ...]:
        raise NotImplementedError


class NullPostStructureClient:''',
    )


def main() -> int:
    """Apply every reviewed source transformation exactly once."""

    _write_catalog_sql_helper()
    _repair_customer_hint_ingestion()
    _repair_demo_scope()
    _repair_entity_relationship_ingestion()
    _repair_synthetic_seed_cleanup()
    _repair_backfill_post_content()
    _repair_backfill_post_keymen()
    _repair_backfill_post_summaries()
    _repair_protocol_stub()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
