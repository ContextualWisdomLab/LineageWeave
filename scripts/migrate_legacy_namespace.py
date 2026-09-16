#!/usr/bin/env python3
"""Migrate stored ``post_project_mention.ontology_iri`` values onto the
canonical repository-case namespace.

ADR 0207 supersedes ADR 0157 and makes
``https://contextualwisdomlab.github.io/LineageWeave/ontology#`` canonical
-- the exact project path GitHub Pages serves -- while demoting
``https://contextualwisdomlab.github.io/lineageweave/ontology#`` to a
deprecated compatibility namespace. New writes mint only canonical IRIs
(``lineageweave.ontology`` loads the repository-case graph), but rows
written before this decision can still carry lowercase IRIs. RDF consumers
treat the two spellings as different resources, so leaving them split makes
downstream joins miss mentions that are semantically identical.

This tool is deliberately *not* silent:

- default mode is **dry run**: it prints every row it would change and exits;
- ``--apply`` performs exactly the printed rewrites inside one transaction;
- the extraction provenance columns (``extraction_method``, confidence,
  evidence text) are never touched -- only the IRI spelling moves, so the
  evidence chain of who extracted what remains intact per ADR 0207's
  "do not silently rewrite historical evidence" rule;
- any IRI outside the two known namespaces is reported and left alone so an
  unexpected third spelling cannot be bulk-mangled;
- the operation is idempotent -- rerunning on a migrated database reports
  ``no legacy namespace rows remain`` and writes nothing.

Usage::

    python scripts/migrate_legacy_namespace.py --dsn postgresql://...
    python scripts/migrate_legacy_namespace.py --dsn postgresql://... --apply
"""

from __future__ import annotations

import argparse
import sys

import asyncpg

CANONICAL_NAMESPACE = "https://contextualwisdomlab.github.io/LineageWeave/ontology#"
LEGACY_NAMESPACE = "https://contextualwisdomlab.github.io/lineageweave/ontology#"


def canonicalize_ontology_iri(ontology_iri: str) -> str | None:
    """Return the canonical spelling of an IRI, or None if it is not legacy."""
    if ontology_iri.startswith(LEGACY_NAMESPACE):
        return CANONICAL_NAMESPACE + ontology_iri[len(LEGACY_NAMESPACE) :]
    return None


async def migrate_legacy_ontology_namespace(
    target_dsn: str,
    apply_changes: bool,
) -> int:
    """Scan, report, and optionally rewrite legacy namespace IRIs.

    Args:
        target_dsn: PostgreSQL DSN for the target database.
        apply_changes: False for dry-run reporting; True to execute the rewrite.

    Returns:
        Process exit code: 0 when clean or migrated, 1 on unexpected IRIs.
    """
    database_connection = await asyncpg.connect(target_dsn)
    try:
        source_mention_rows = await database_connection.fetch(
            """
            select post_id, project_name, ontology_iri
            from post_project_mention
            where ontology_iri is not null
            order by post_id, project_name
            """
        )
        unexpected_namespace_records: list[tuple[str, str, str]] = []
        planned_iri_rewrites: list[tuple[str, str, str]] = []
        for source_mention_row in source_mention_rows:
            ontology_iri = source_mention_row["ontology_iri"]
            canonical_ontology_iri = canonicalize_ontology_iri(ontology_iri)
            if canonical_ontology_iri is None:
                if not ontology_iri.startswith(CANONICAL_NAMESPACE):
                    unexpected_namespace_records.append(
                        (
                            source_mention_row["post_id"],
                            source_mention_row["project_name"],
                            ontology_iri,
                        )
                    )
                continue
            planned_iri_rewrites.append(
                (
                    source_mention_row["post_id"],
                    source_mention_row["project_name"],
                    f"{ontology_iri} -> {canonical_ontology_iri}",
                )
            )

        print(
            f"scanned {len(source_mention_rows)} mention row(s) "
            "with a non-null ontology_iri"
        )
        for post_id, project_name, iri_rewrite_description in planned_iri_rewrites:
            print(f"  {post_id} / {project_name}: {iri_rewrite_description}")
        for post_id, project_name, ontology_iri in unexpected_namespace_records:
            print(
                f"  UNEXPECTED {post_id} / {project_name}: {ontology_iri} "
                f"(neither namespace; left untouched)"
            )
        if unexpected_namespace_records:
            print(
                f"{len(unexpected_namespace_records)} row(s) carry an unrecognized "
                "namespace; nothing written"
            )
            return 1
        if not planned_iri_rewrites:
            print("no legacy namespace rows remain")
            return 0
        if not apply_changes:
            print(
                f"dry run: {len(planned_iri_rewrites)} row(s) would be rewritten; "
                "pass --apply to write"
            )
            return 0

        async with database_connection.transaction():
            for post_id, project_name, iri_rewrite_description in planned_iri_rewrites:
                _legacy_ontology_iri, _, canonical_ontology_iri = (
                    iri_rewrite_description.rpartition(" -> ")
                )
                database_update_result = await database_connection.execute(
                    """
                    update post_project_mention
                    set ontology_iri = $3
                    where post_id = $1 and project_name = $2 and ontology_iri = $4
                    """,
                    post_id,
                    project_name,
                    canonical_ontology_iri,
                    canonical_ontology_iri.replace(
                        CANONICAL_NAMESPACE,
                        LEGACY_NAMESPACE,
                    ),
                )
                if database_update_result != "UPDATE 1":
                    raise RuntimeError(
                        f"row changed during migration: {post_id}/{project_name}"
                    )
        print(
            f"applied: {len(planned_iri_rewrites)} row(s) rewritten "
            "to the canonical namespace"
        )
        return 0
    finally:
        await database_connection.close()


def main(raw_arguments: list[str] | None = None) -> int:
    """CLI entry point."""
    command_parser = argparse.ArgumentParser(description=__doc__)
    command_parser.add_argument(
        "--dsn",
        required=True,
        help="PostgreSQL DSN for the target database",
    )
    command_parser.add_argument(
        "--apply",
        action="store_true",
        help="execute the rewrite; without this flag the tool only reports",
    )
    command_arguments = command_parser.parse_args(raw_arguments)
    return __import__("asyncio").run(
        migrate_legacy_ontology_namespace(
            command_arguments.dsn,
            command_arguments.apply,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
