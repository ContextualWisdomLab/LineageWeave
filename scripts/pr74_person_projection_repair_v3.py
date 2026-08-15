#!/usr/bin/env python3
"""Complete the PR #74 repair across fresh installs and synthetic seeding."""

from __future__ import annotations

import pr74_person_projection_repair_v2 as repair


def _postprocess_schema() -> None:
    """Keep the upgrade migration idempotent and avoid duplicate unique indexes."""

    for path in (
        "migrations/0001_initial_schema.sql",
        "migrations/0016_cross_post_actor_identity.sql",
    ):
        text = repair.base._read(path)
        text = text.replace(
            "create table knowledge_graph_edge_evidence (",
            "create table if not exists knowledge_graph_edge_evidence (",
        )
        text = text.replace(
            "create index knowledge_graph_edge_evidence_post_idx",
            "create index if not exists knowledge_graph_edge_evidence_post_idx",
        )
        repair.base._write(path, text)

    path = "migrations/0001_initial_schema.sql"
    text = repair.base._read(path)
    unnamed = (
        "    unique (\n"
        "        source_node_type_code, source_node_id,\n"
        "        target_node_type_code, target_node_id,\n"
        "        edge_type_code\n"
        "    )\n"
    )
    named = (
        "    constraint knowledge_graph_edge_identity_uq unique (\n"
        "        source_node_type_code, source_node_id,\n"
        "        target_node_type_code, target_node_id,\n"
        "        edge_type_code\n"
        "    )\n"
    )
    text = repair.base._replace_once(
        text, unnamed, named, "named knowledge graph identity constraint"
    )
    repair.base._write(path, text)


def _update_seed() -> None:
    """Seed both evidence channels and let database triggers register support."""

    path = "scripts/seed_demo_data.py"
    text = repair.base._read(path)
    text = repair.base._replace_once(
        text,
        '    cur.execute("delete from post_summary_result where post_id = %s", (post_id,))\n',
        '    cur.execute("delete from post_summary_person_mention where post_id = %s", (post_id,))\n'
        '    cur.execute("delete from post_summary_result where post_id = %s", (post_id,))\n',
        "seed summary replacement start",
    )
    function_start = text.index("def _write_post_summary(cur, post_id, summary) -> None:")
    function_end = text.index("\n\ndef _write_post_chat", function_start)
    block = text[function_start:function_end]
    projection_sql = '''
    cur.execute(
        """
        insert into post_summary_person_mention (post_id, person_id)
        select distinct role.post_id, matched_person.person_id
          from post_summary_role role
          join lateral (
                select person.person_id
                  from cataloged_person person
                 where person.person_name = role.actor_name
                 order by person.created_at, person.person_id
                 limit 1
          ) matched_person on true
         where role.post_id = %s
           and role.actor_type_code = 'prov_person'
        on conflict do nothing
        """,
        (post_id,),
    )
'''
    block = block.rstrip() + "\n" + projection_sql
    text = text[:function_start] + block + text[function_end:]

    order_old = (
        "            _seed_fixture_summaries(cur)\n"
        "            _seed_fixture_chats(cur)\n"
        "            _seed_fixture_evaluations(cur)\n"
        "            _seed_fixture_keymen_and_voc(cur, corporate_entity_id)\n"
    )
    order_new = (
        "            _seed_fixture_keymen_and_voc(cur, corporate_entity_id)\n"
        "            _seed_fixture_summaries(cur)\n"
        "            _seed_fixture_chats(cur)\n"
        "            _seed_fixture_evaluations(cur)\n"
    )
    text = repair.base._replace_once(text, order_old, order_new, "fixture seed order")
    demo_reconcile_anchor = "\n            _seed_reconstructed_lineage(\n"
    text = repair.base._replace_once(
        text,
        demo_reconcile_anchor,
        "\n            _seed_demo_public_summary(cur, demo_public_post_id)\n"
        + demo_reconcile_anchor,
        "demo summary reconciliation point",
    )
    repair.base._write(path, text)


def main() -> int:
    """Run the core repair, then harden fresh-install and seed behavior."""

    repair.base.EDGE_EVIDENCE_SCHEMA = repair.base.EDGE_EVIDENCE_SCHEMA.replace(
        "create table knowledge_graph_edge_evidence (",
        "create table if not exists knowledge_graph_edge_evidence (",
    ).replace(
        "create index knowledge_graph_edge_evidence_post_idx",
        "create index if not exists knowledge_graph_edge_evidence_post_idx",
    )
    result = repair.main()
    _postprocess_schema()
    _update_seed()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
