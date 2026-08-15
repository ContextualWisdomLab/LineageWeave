#!/usr/bin/env python3
"""Run the PR #74 repair with indentation-safe source transforms."""

from __future__ import annotations

import pr74_person_projection_repair as base


def update_summary_writer() -> None:
    """Separate R&R people from Keymen and always reconcile graph support."""

    path = "backend/app/post_summary_ingestion.py"
    text = base._read(path)
    old_doc = (
        "A person actor is opportunistically joined to an *existing*\n"
        "``cataloged_person`` row by name when Keyman extraction has already\n"
        "cataloged that name -- R&R does not originate new person identities\n"
        "itself (it has no reliable ``person_side_code`` to create one with; see\n"
        "ADR 0009's documented follow-up)."
    )
    new_doc = (
        "A person actor is opportunistically joined to an *existing*\n"
        "``cataloged_person`` row by name when Keyman extraction has already\n"
        "cataloged that name. The R&R evidence is written to\n"
        "``post_summary_person_mention`` rather than Keyman's\n"
        "``post_person_mention`` so either extractor can replace its own result\n"
        "without leaving or deleting the other's evidence."
    )
    text = base._replace_once(text, old_doc, new_doc, "summary person-source docstring")

    delete_start = text.index(
        "    # Summary replacement also replaces its team/organization projections."
    )
    delete_end = text.index(
        '    await conn.execute("delete from post_team_mention', delete_start
    )
    replacement = (
        "    # Summary replacement owns only R&R projections. Keyman mentions remain\n"
        "    # independent and are combined only by the graph read/derivation view.\n"
        "    await conn.execute(\n"
        '        "delete from post_summary_person_mention where post_id = $1",\n'
        "        post_id,\n"
        "    )\n"
    )
    text = text[:delete_start] + replacement + text[delete_end:]

    text = base._replace_once(
        text,
        '"insert into post_person_mention (post_id, person_id) "',
        '"insert into post_summary_person_mention (post_id, person_id) "',
        "R&R person insert target",
    )
    text = base._replace_once(
        text,
        "    if summary.roles_and_responsibilities:\n"
        "        await persist_edges_for_post(conn, post_id)\n",
        "    await persist_edges_for_post(conn, post_id)\n",
        "summary graph guard",
    )
    base._write(path, text)


def update_main_endpoint() -> None:
    """Defer KG reconciliation until all extraction writes are complete."""

    path = "backend/app/main.py"
    text = base._read(path)
    text = base._replace_once(
        text,
        "    person_exists,\n    related_for_entity,",
        "    person_exists,\n    persist_edges_for_post,\n    related_for_entity,",
        "KG import list",
    )
    text = base._replace_once(
        text,
        "                hierarchy_inference_client=_corporate_hierarchy_inference_client(),\n"
        "            )\n",
        "                hierarchy_inference_client=_corporate_hierarchy_inference_client(),\n"
        "                persist_graph=False,\n"
        "            )\n",
        "Keyman endpoint call",
    )
    relationship_start = text.index(
        "            relationships = await ingest_post_entity_relationships("
    )
    relationship_end = text.index("\n            )", relationship_start) + len(
        "\n            )"
    )
    text = (
        text[:relationship_end]
        + "\n            await persist_edges_for_post(conn, post_id)"
        + text[relationship_end:]
    )
    base._write(path, text)


def main() -> int:
    """Replace the two indentation-sensitive transforms, then run the repair."""

    base.update_summary_writer = update_summary_writer
    base.update_main_endpoint = update_main_endpoint
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
