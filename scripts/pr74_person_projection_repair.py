#!/usr/bin/env python3
"""Apply the test-first PR #74 person/KG projection repair.

This helper exists only on the repair branch. The one-shot workflow removes it
before producing the reviewed product commit.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"expected exactly one {label}; found {text.count(old)}")
    return text.replace(old, new, 1)


def _replace_between(text: str, start: str, end: str, replacement: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[:start_index] + replacement.rstrip() + "\n\n" + text[end_index:]


PERSON_PROJECTION_SCHEMA = dedent(
    '''\
    create table post_summary_person_mention (
        post_id uuid not null references source_post (post_id) on delete cascade,
        person_id uuid not null references cataloged_person (person_id),
        primary key (post_id, person_id)
    );

    -- Read-side union only. The two writable tables retain the evidence source:
    -- post_person_mention is Keyman extraction; post_summary_person_mention is R&R.
    create view combined_post_person_mention as
        select post_id, person_id from post_person_mention
        union
        select post_id, person_id from post_summary_person_mention;
    '''
).rstrip()


EDGE_EVIDENCE_SCHEMA = dedent(
    '''\
    create table knowledge_graph_edge_evidence (
        knowledge_graph_edge_id uuid not null
            references knowledge_graph_edge (knowledge_graph_edge_id) on delete cascade,
        evidence_post_id uuid not null references source_post (post_id) on delete cascade,
        primary key (knowledge_graph_edge_id, evidence_post_id)
    );

    create index knowledge_graph_edge_evidence_post_idx
        on knowledge_graph_edge_evidence (evidence_post_id, knowledge_graph_edge_id);

    create or replace function register_knowledge_graph_edge_evidence()
    returns trigger
    language plpgsql
    as $$
    begin
        if new.edge_type_code in (
            'edge_mention',
            'edge_mention_team',
            'edge_mention_organization'
        ) and new.target_node_type_code = 'node_post' then
            insert into knowledge_graph_edge_evidence
                (knowledge_graph_edge_id, evidence_post_id)
            values (new.knowledge_graph_edge_id, new.target_node_id)
            on conflict do nothing;
        elsif new.edge_type_code = 'edge_co_mention' then
            insert into knowledge_graph_edge_evidence
                (knowledge_graph_edge_id, evidence_post_id)
            select distinct new.knowledge_graph_edge_id, left_mention.post_id
              from combined_post_person_mention left_mention
              join combined_post_person_mention right_mention
                on right_mention.post_id = left_mention.post_id
             where left_mention.person_id = new.source_node_id
               and right_mention.person_id = new.target_node_id
            on conflict do nothing;
        elsif new.edge_type_code = 'edge_affiliation' then
            insert into knowledge_graph_edge_evidence
                (knowledge_graph_edge_id, evidence_post_id)
            select distinct new.knowledge_graph_edge_id, mention.post_id
              from combined_post_person_mention mention
              join person_affiliation affiliation
                on affiliation.person_id = mention.person_id
             where mention.person_id = new.source_node_id
               and affiliation.affiliated_corporate_entity_id = new.target_node_id
            on conflict do nothing;
        elsif new.edge_type_code = 'edge_team_affiliation' then
            insert into knowledge_graph_edge_evidence
                (knowledge_graph_edge_id, evidence_post_id)
            select distinct new.knowledge_graph_edge_id, mention.post_id
              from post_team_mention mention
              join cataloged_team team on team.team_id = mention.team_id
             where mention.team_id = new.source_node_id
               and team.affiliated_corporate_entity_id = new.target_node_id
            on conflict do nothing;
        end if;
        return new;
    end
    $$;

    drop trigger if exists knowledge_graph_edge_evidence_register
        on knowledge_graph_edge;
    create trigger knowledge_graph_edge_evidence_register
    after insert or update on knowledge_graph_edge
    for each row execute function register_knowledge_graph_edge_evidence();
    '''
).rstrip()


def update_initial_schema() -> None:
    path = "migrations/0001_initial_schema.sql"
    text = _read(path)
    mention_anchor = dedent(
        '''\
        create table post_person_mention (
            post_id uuid not null references source_post (post_id),
            person_id uuid not null references cataloged_person (person_id),
            mention_context text,
            primary key (post_id, person_id)
        );
        '''
    ).rstrip()
    text = _replace_once(
        text,
        mention_anchor,
        mention_anchor + "\n\n" + PERSON_PROJECTION_SCHEMA,
        "post_person_mention schema anchor",
    )
    edge_tail = dedent(
        '''\
            edge_type_code text not null references common_lookup_value (lookup_code),
            edge_weight numeric not null default 1.0,
            created_at timestamptz not null default now()
        );
        '''
    ).rstrip()
    edge_tail_replacement = dedent(
        '''\
            edge_type_code text not null references common_lookup_value (lookup_code),
            edge_weight numeric not null default 1.0,
            created_at timestamptz not null default now(),
            unique (
                source_node_type_code, source_node_id,
                target_node_type_code, target_node_id,
                edge_type_code
            )
        );
        '''
    ).rstrip()
    text = _replace_once(text, edge_tail, edge_tail_replacement, "knowledge graph edge tail")
    edge_index_anchor = dedent(
        '''\
        create index knowledge_graph_edge_source_idx on knowledge_graph_edge (source_node_type_code, source_node_id);
        create index knowledge_graph_edge_target_idx on knowledge_graph_edge (target_node_type_code, target_node_id);
        '''
    ).rstrip()
    text = _replace_once(
        text,
        edge_index_anchor,
        edge_index_anchor + "\n\n" + EDGE_EVIDENCE_SCHEMA,
        "knowledge graph indexes",
    )
    _write(path, text)


def update_upgrade_migration() -> None:
    path = "migrations/0016_cross_post_actor_identity.sql"
    text = _read(path)
    addition = dedent(
        f'''\

        -- Keyman and R&R person mentions are independent replaceable evidence
        -- channels. Existing rows matching a current R&R role are conservatively
        -- reclassified to R&R; a later Keyman extraction repopulates its own set.
        create table if not exists post_summary_person_mention (
            post_id uuid not null references source_post (post_id) on delete cascade,
            person_id uuid not null references cataloged_person (person_id),
            primary key (post_id, person_id)
        );

        create or replace view combined_post_person_mention as
            select post_id, person_id from post_person_mention
            union
            select post_id, person_id from post_summary_person_mention;

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
         where role.actor_type_code = 'prov_person'
        on conflict do nothing;

        delete from post_person_mention keyman_mention
         using post_summary_person_mention summary_mention
         where keyman_mention.post_id = summary_mention.post_id
           and keyman_mention.person_id = summary_mention.person_id;

        with ranked_edge as (
            select knowledge_graph_edge_id,
                   row_number() over (
                       partition by source_node_type_code, source_node_id,
                                    target_node_type_code, target_node_id,
                                    edge_type_code
                       order by created_at, knowledge_graph_edge_id
                   ) as duplicate_rank
              from knowledge_graph_edge
        )
        delete from knowledge_graph_edge edge_row
         using ranked_edge duplicate
         where edge_row.knowledge_graph_edge_id = duplicate.knowledge_graph_edge_id
           and duplicate.duplicate_rank > 1;

        create unique index if not exists knowledge_graph_edge_identity_uq
            on knowledge_graph_edge (
                source_node_type_code, source_node_id,
                target_node_type_code, target_node_id,
                edge_type_code
            );

        {EDGE_EVIDENCE_SCHEMA}

        -- Re-run the support trigger for every surviving legacy edge, then prune
        -- rows that cannot be tied to current post evidence.
        update knowledge_graph_edge set edge_weight = edge_weight;
        delete from knowledge_graph_edge edge_row
         where not exists (
             select 1
               from knowledge_graph_edge_evidence evidence
              where evidence.knowledge_graph_edge_id = edge_row.knowledge_graph_edge_id
         );
        '''
    ).rstrip()
    text = text.rstrip() + addition + "\n"
    _write(path, text)


def update_knowledge_graph_repository() -> None:
    path = "backend/app/knowledge_graph.py"
    text = _read(path)
    import_anchor = "from lineageweave.knowledge_graph import (\n"
    lock_definition = '_GRAPH_PROJECTION_LOCK_KEY = "lineageweave:knowledge_graph_projection"\n\n\n'
    class_anchor = "\ndef edge_spec_from_row(row: asyncpg.Record) -> KnowledgeGraphEdgeSpec:\n"
    if lock_definition not in text:
        text = _replace_once(text, class_anchor, "\n" + lock_definition + class_anchor.lstrip("\n"), "edge mapper anchor")

    persist_function = dedent(
        '''\
        async def persist_edges_for_post(
            conn: asyncpg.Connection, post_id: str
        ) -> list[KnowledgeGraphEdgeSpec]:
            """Reconcile one post's evidence-backed navigation projection.

            Callers own the surrounding transaction. A transaction-scoped
            advisory lock serializes the small materialized projection so two
            writers cannot interleave evidence deletion and orphan pruning.
            Keyman and R&R person sources stay distinct in their writable tables;
            ``combined_post_person_mention`` is used only to derive graph edges.
            """
            await conn.execute(
                "select pg_advisory_xact_lock(hashtext($1))",
                _GRAPH_PROJECTION_LOCK_KEY,
            )
            await conn.execute(
                "delete from knowledge_graph_edge_evidence where evidence_post_id = $1",
                post_id,
            )
            mention_rows = await conn.fetch(
                "select person_id from combined_post_person_mention where post_id = $1",
                post_id,
            )
            affiliation_rows = await conn.fetch(
                """
                select person_id, affiliated_corporate_entity_id
                from person_affiliation
                where person_id = any($1::uuid[])
                  and affiliated_corporate_entity_id is not null
                """,
                [row["person_id"] for row in mention_rows],
            )
            team_mention_rows = await conn.fetch(
                "select team_id from post_team_mention where post_id = $1",
                post_id,
            )
            team_affiliation_rows = await conn.fetch(
                """
                select team_id, affiliated_corporate_entity_id
                from cataloged_team
                where team_id = any($1::uuid[])
                  and affiliated_corporate_entity_id is not null
                """,
                [row["team_id"] for row in team_mention_rows],
            )
            organization_mention_rows = await conn.fetch(
                "select corporate_entity_id from post_organization_mention where post_id = $1",
                post_id,
            )
            edges = knowledge_graph_edges_for_post(
                post_id,
                [str(row["person_id"]) for row in mention_rows],
                [
                    (str(row["person_id"]), str(row["affiliated_corporate_entity_id"]))
                    for row in affiliation_rows
                ],
                [str(row["team_id"]) for row in team_mention_rows],
                [
                    (str(row["team_id"]), str(row["affiliated_corporate_entity_id"]))
                    for row in team_affiliation_rows
                ],
                [str(row["corporate_entity_id"]) for row in organization_mention_rows],
            )
            for edge in edges:
                await conn.fetchrow(
                    """
                    insert into knowledge_graph_edge (
                        source_node_type_code, source_node_id,
                        target_node_type_code, target_node_id,
                        edge_type_code, edge_weight
                    ) values ($1, $2::uuid, $3, $4::uuid, $5, $6)
                    on conflict (
                        source_node_type_code, source_node_id,
                        target_node_type_code, target_node_id,
                        edge_type_code
                    ) do update set edge_weight = excluded.edge_weight
                    returning knowledge_graph_edge_id
                    """,
                    edge.source_node_type_code,
                    edge.source_node_id,
                    edge.target_node_type_code,
                    edge.target_node_id,
                    edge.edge_type_code,
                    edge.edge_weight,
                )
            await conn.execute(
                """
                delete from knowledge_graph_edge edge_row
                 where not exists (
                     select 1
                       from knowledge_graph_edge_evidence evidence
                      where evidence.knowledge_graph_edge_id =
                            edge_row.knowledge_graph_edge_id
                 )
                """
            )
            return edges
        '''
    )
    text = _replace_between(text, "async def persist_edges_for_post(", "async def person_exists(", persist_function)

    visible_mention = dedent(
        '''\
        async def visible_mention_post_ids(
            conn: asyncpg.Connection,
            person_id: str,
            can_see_post,
        ) -> list[str]:
            """Visible post ids supported by Keyman or R&R person evidence."""
            rows = await conn.fetch(
                """
                select post.post_id, post.visibility_code, post.corporate_entity_id
                  from combined_post_person_mention mention
                  join source_post post on post.post_id = mention.post_id
                 where mention.person_id = $1
                 order by post.created_at, post.post_id
                """,
                person_id,
            )
            return [str(row["post_id"]) for row in rows if can_see_post(row)]
        '''
    )
    text = _replace_between(text, "async def visible_mention_post_ids(", "async def visible_affiliation_post_ids(", visible_mention)

    visible_affiliation = dedent(
        '''\
        async def visible_affiliation_post_ids(
            conn: asyncpg.Connection,
            entity_id: str,
            can_see_post,
        ) -> list[str]:
            """Visible posts whose Keyman or R&R people affiliate with an entity."""
            rows = await conn.fetch(
                """
                select distinct post.post_id, post.visibility_code,
                                post.corporate_entity_id, post.created_at
                  from person_affiliation affiliation
                  join combined_post_person_mention mention
                    on mention.person_id = affiliation.person_id
                  join source_post post on post.post_id = mention.post_id
                 where affiliation.affiliated_corporate_entity_id = $1
                 order by post.created_at, post.post_id
                """,
                entity_id,
            )
            return [str(row["post_id"]) for row in rows if can_see_post(row)]
        '''
    )
    text = _replace_between(text, "async def visible_affiliation_post_ids(", "async def load_visible_subgraph(", visible_affiliation)

    load_subgraph = dedent(
        '''\
        async def load_visible_subgraph(
            conn: asyncpg.Connection,
            visible_post_ids: list[str],
        ) -> list[KnowledgeGraphEdgeSpec]:
            """Edges supported by at least one post the account may already see."""
            if not visible_post_ids:
                return []
            person_rows = await conn.fetch(
                "select distinct person_id from combined_post_person_mention "
                "where post_id = any($1::uuid[])",
                visible_post_ids,
            )
            person_ids = [row["person_id"] for row in person_rows]
            if not person_ids:
                return []
            rows = await conn.fetch(
                """
                select distinct edge.source_node_type_code, edge.source_node_id,
                       edge.target_node_type_code, edge.target_node_id,
                       edge.edge_type_code, edge.edge_weight
                  from knowledge_graph_edge edge
                  join knowledge_graph_edge_evidence evidence
                    on evidence.knowledge_graph_edge_id = edge.knowledge_graph_edge_id
                   and evidence.evidence_post_id = any($1::uuid[])
                 where
                  (
                    edge.edge_type_code = $3
                    and (
                      (edge.source_node_type_code = $4
                       and edge.source_node_id = any($1::uuid[]))
                      or
                      (edge.target_node_type_code = $4
                       and edge.target_node_id = any($1::uuid[]))
                    )
                  )
                  or (
                    edge.edge_type_code = $5
                    and edge.source_node_type_code = $6
                    and edge.target_node_type_code = $6
                    and edge.source_node_id = any($2::uuid[])
                    and edge.target_node_id = any($2::uuid[])
                  )
                  or (
                    edge.edge_type_code = $7
                    and (
                      (edge.source_node_type_code = $6
                       and edge.source_node_id = any($2::uuid[]))
                      or
                      (edge.target_node_type_code = $6
                       and edge.target_node_id = any($2::uuid[]))
                    )
                  )
                """,
                visible_post_ids,
                person_ids,
                EDGE_MENTION,
                NODE_POST,
                EDGE_CO_MENTION,
                NODE_PERSON,
                EDGE_AFFILIATION,
            )
            return [edge_spec_from_row(row) for row in rows]
        '''
    )
    text = _replace_between(text, "async def load_visible_subgraph(", "async def hydrate_related_nodes(", load_subgraph)
    _write(path, text)


def update_summary_writer() -> None:
    path = "backend/app/post_summary_ingestion.py"
    text = _read(path)
    old_doc = "A person actor is opportunistically joined to an *existing*\n``cataloged_person`` row by name when Keyman extraction has already\ncataloged that name -- R&R does not originate new person identities\nitself (it has no reliable ``person_side_code`` to create one with; see\nADR 0009's documented follow-up)."
    new_doc = "A person actor is opportunistically joined to an *existing*\n``cataloged_person`` row by name when Keyman extraction has already\ncataloged that name. The R&R evidence is written to\n``post_summary_person_mention`` rather than Keyman's\n``post_person_mention`` so either extractor can replace its own result\nwithout leaving or deleting the other's evidence."
    text = _replace_once(text, old_doc, new_doc, "summary person-source docstring")

    delete_start = text.index("    # Summary replacement also replaces its team/organization projections.")
    delete_end = text.index("    await conn.execute(\"delete from post_team_mention", delete_start)
    replacement = dedent(
        '''\
            # Summary replacement owns only R&R projections. Keyman mentions remain
            # independent and are combined only by the graph read/derivation view.
            await conn.execute(
                "delete from post_summary_person_mention where post_id = $1",
                post_id,
            )
        '''
    )
    text = text[:delete_start] + replacement + text[delete_end:]

    person_insert = dedent(
        '''\
                    await conn.execute(
                        "insert into post_person_mention (post_id, person_id) "
                        "values ($1, $2) on conflict do nothing",
                        post_id,
                        str(person_row["person_id"]),
                    )
        '''
    )
    person_insert_replacement = dedent(
        '''\
                    await conn.execute(
                        "insert into post_summary_person_mention (post_id, person_id) "
                        "values ($1, $2) on conflict do nothing",
                        post_id,
                        str(person_row["person_id"]),
                    )
        '''
    )
    text = _replace_once(text, person_insert, person_insert_replacement, "R&R person insert")
    guarded_edges = "    if summary.roles_and_responsibilities:\n        await persist_edges_for_post(conn, post_id)\n"
    text = _replace_once(
        text,
        guarded_edges,
        "    await persist_edges_for_post(conn, post_id)\n",
        "summary graph guard",
    )
    _write(path, text)


def update_keyman_writer() -> None:
    path = "backend/app/keyman_ingestion.py"
    text = _read(path)
    signature_anchor = "    hierarchy_inference_client: CorporateHierarchyInferenceClient | None = None,\n) -> list[PersonMention]:"
    signature_replacement = "    hierarchy_inference_client: CorporateHierarchyInferenceClient | None = None,\n    persist_graph: bool = True,\n) -> list[PersonMention]:"
    text = _replace_once(text, signature_anchor, signature_replacement, "Keyman signature")
    normalized_anchor = "    normalized_mentions: list[PersonMention] = []\n\n    for mention in mentions:\n"
    normalized_replacement = (
        "    normalized_mentions: list[PersonMention] = []\n"
        "    await conn.execute(\n"
        "        \"delete from post_person_mention where post_id = $1\", post_id\n"
        "    )\n\n"
        "    for mention in mentions:\n"
    )
    text = _replace_once(text, normalized_anchor, normalized_replacement, "Keyman replacement anchor")
    graph_guard = "    if normalized_mentions:\n        await persist_edges_for_post(conn, post_id)\n\n    return normalized_mentions\n"
    graph_replacement = "    if persist_graph:\n        await persist_edges_for_post(conn, post_id)\n\n    return normalized_mentions\n"
    text = _replace_once(text, graph_guard, graph_replacement, "Keyman graph guard")
    doc_anchor = "    `resolution_client`/`verification_client`/`hierarchy_inference_client`\n    default to the unavailable Null clients -- callers that don't pass\n    real ones get the exact same behavior as before ADR 0008/0010 (raw\n    affiliation names, unresolved).\n"
    doc_replacement = doc_anchor + "\n    The post's prior Keyman mention set is replaced atomically after a successful\n    extraction. ``persist_graph=False`` lets a larger caller defer graph\n    reconciliation until the end of its own transaction.\n"
    text = _replace_once(text, doc_anchor, doc_replacement, "Keyman replacement docstring")
    _write(path, text)


def update_main_endpoint() -> None:
    path = "backend/app/main.py"
    text = _read(path)
    import_anchor = "    person_exists,\n    related_for_entity,"
    import_replacement = "    person_exists,\n    persist_edges_for_post,\n    related_for_entity,"
    text = _replace_once(text, import_anchor, import_replacement, "KG import list")
    call_anchor = "                hierarchy_inference_client=_corporate_hierarchy_inference_client(),\n            )\n"
    call_replacement = "                hierarchy_inference_client=_corporate_hierarchy_inference_client(),\n                persist_graph=False,\n            )\n"
    text = _replace_once(text, call_anchor, call_replacement, "Keyman endpoint call")
    relationship_anchor = dedent(
        '''\
                    relationships = await ingest_post_entity_relationships(
                        conn, relationship_client, post_id, post["post_title"], post_body, organization_names
                    )
        '''
    )
    relationship_replacement = relationship_anchor + "            await persist_edges_for_post(conn, post_id)\n"
    text = _replace_once(text, relationship_anchor, relationship_replacement, "relationship endpoint tail")
    _write(path, text)


def update_chat_reader() -> None:
    path = "backend/app/post_chat_ingestion.py"
    text = _read(path)
    text = _replace_once(
        text,
        '        "select distinct person_id from post_person_mention where post_id = $1", post_id\n',
        '        "select distinct person_id from combined_post_person_mention where post_id = $1", post_id\n',
        "chat person discovery query",
    )
    text = _replace_once(
        text,
        '            "select distinct post_id from post_person_mention where person_id = any($1::uuid[])",\n',
        '            "select distinct post_id from combined_post_person_mention "\n            "where person_id = any($1::uuid[])",\n',
        "chat sibling discovery query",
    )
    _write(path, text)


def update_tests_and_docs() -> None:
    schema_path = "tests/test_schema.py"
    schema = _read(schema_path)
    table_anchor = '        "post_person_mention",\n        "knowledge_graph_edge",\n'
    table_replacement = (
        '        "post_person_mention",\n'
        '        "post_summary_person_mention",\n'
        '        "knowledge_graph_edge",\n'
        '        "knowledge_graph_edge_evidence",\n'
    )
    schema = _replace_once(schema, table_anchor, table_replacement, "schema expected tables")
    _write(schema_path, schema)

    transaction_path = "tests/test_ingestion_transaction_contracts.py"
    transaction = _read(transaction_path)
    transaction = _replace_once(
        transaction,
        '        "delete from knowledge_graph_edge",\n        "delete from post_team_mention",\n',
        '        "delete from post_summary_person_mention",\n        "delete from post_team_mention",\n',
        "summary transaction SQL expectations",
    )
    _write(transaction_path, transaction)

    adr_path = "docs/adr/0009-cross-post-actor-identity.md"
    adr = _read(adr_path)
    person_paragraph = dedent(
        '''\
        **Person** (an R&R actor, not a Keyman): opportunistically joined to an
        *existing* `cataloged_person` row by exact name match, when Keyman
        extraction has already cataloged that name on this or another post.
        R&R does not create a new person identity itself -- `cataloged_person`
        requires `person_side_code` (our-side vs. counterparty), which R&R's
        prompt does not currently ask for and Keyman's does; inventing one here
        risked a wrong side assignment. Documented as a real, deliberate scope
        boundary below, not silently half-done.
        '''
    ).rstrip()
    person_replacement = person_paragraph + dedent(
        '''\

        Person evidence sources remain separate: Keyman extraction replaces
        `post_person_mention`; R&R replacement writes
        `post_summary_person_mention`. `combined_post_person_mention` is a
        read-only union used for lineage and KG derivation. This prevents a new
        summary from deleting Keyman evidence and prevents removed R&R actors
        from surviving as stale Keymen.
        '''
    )
    adr = _replace_once(adr, person_paragraph, person_replacement, "ADR person decision")
    edge_paragraph = "Each resolved actor gets a real Knowledge Graph mention edge (new\n`edge_mention_team` / `edge_team_affiliation` / `edge_mention_organization`\nlookup codes, `lineageweave/knowledge_graph.py`'s\n`knowledge_graph_edges_for_post` extended, not a second edge-writing\npath), reusing the same `persist_edges_for_post` entry point Keyman\ningestion already calls -- one function computes a post's whole edge\nset regardless of which extraction step triggered it."
    edge_replacement = edge_paragraph + "\n\n`knowledge_graph_edge` is a deduplicated materialized registry.\n`knowledge_graph_edge_evidence` records every post that currently supports an\nedge; readers require support from an ABAC-visible post. Writers reconcile one\npost under a transaction-scoped advisory lock, and unsupported registry rows\nare pruned. Edge identity therefore cannot duplicate under concurrency, and a\nreplacement cannot leave a buyer-visible orphan edge."
    adr = _replace_once(adr, edge_paragraph, edge_replacement, "ADR edge decision")
    _write(adr_path, adr)

    architecture_path = "ARCHITECTURE.md"
    architecture = _read(architecture_path)
    architecture_anchor = "`post_person_mention`"
    first_index = architecture.find(architecture_anchor)
    if first_index == -1:
        raise RuntimeError("missing architecture person-mention anchor")
    sentence_end = architecture.find("\n", first_index)
    addition = (
        "\n\nKeyman and R&R person mentions are separate replaceable projections "
        "(`post_person_mention` and `post_summary_person_mention`). The read-only "
        "`combined_post_person_mention` view feeds lineage discovery. Materialized "
        "KG edges are unique and carry normalized `knowledge_graph_edge_evidence`; "
        "only evidence from an ABAC-visible post participates in RWR."
    )
    architecture = architecture[:sentence_end] + addition + architecture[sentence_end:]
    _write(architecture_path, architecture)

    changelog_path = "CHANGELOG.md"
    changelog = _read(changelog_path)
    fixed_anchor = "### Fixed\n\n"
    fixed_index = changelog.index(fixed_anchor, changelog.index("## [0.77.0]"))
    bullet = (
        "- Keyman and R&R person mentions now replace independent source projections. "
        "Knowledge Graph edges have one canonical identity plus post-level evidence, "
        "so removed actors and concurrent writes cannot leave stale or duplicate "
        "buyer-visible relationships.\n"
    )
    changelog = changelog[: fixed_index + len(fixed_anchor)] + bullet + changelog[fixed_index + len(fixed_anchor) :]
    _write(changelog_path, changelog)


def main() -> int:
    update_initial_schema()
    update_upgrade_migration()
    update_knowledge_graph_repository()
    update_summary_writer()
    update_keyman_writer()
    update_main_endpoint()
    update_chat_reader()
    update_tests_and_docs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
