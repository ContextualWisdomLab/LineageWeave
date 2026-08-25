#!/usr/bin/env python3
"""Migrate stored ``post_project_mention.ontology_iri`` values onto the
canonical repository-case namespace.

ADR 0205 supersedes ADR 0157 and makes
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
  evidence chain of who extracted what remains intact per ADR 0205's
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


def canonicalize(iri: str) -> str | None:
    """Return the canonical spelling of ``iri``, or None if not legacy."""
    if iri.startswith(LEGACY_NAMESPACE):
        return CANONICAL_NAMESPACE + iri[len(LEGACY_NAMESPACE):]
    return None


async def migrate(dsn: str, apply: bool) -> int:
    """Scan, report, and optionally rewrite legacy namespace IRIs.

    Args:
        dsn: PostgreSQL DSN for the target database.
        apply: False for dry-run reporting; True to execute the rewrite.

    Returns:
        Process exit code: 0 when clean or migrated, 1 on unexpected IRIs.
    """
    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch(
            """
            select post_id, project_name, ontology_iri
            from post_project_mention
            where ontology_iri is not null
            order by post_id, project_name
            """
        )
        unexpected: list[tuple[str, str, str]] = []
        planned: list[tuple[str, str, str]] = []
        for row in rows:
            iri = row["ontology_iri"]
            canonical = canonicalize(iri)
            if canonical is None:
                if not iri.startswith(CANONICAL_NAMESPACE):
                    unexpected.append((row["post_id"], row["project_name"], iri))
                continue
            planned.append((row["post_id"], row["project_name"], f"{iri} -> {canonical}"))

        print(f"scanned {len(rows)} mention row(s) with a non-null ontology_iri")
        for post_id, project_name, change in planned:
            print(f"  {post_id} / {project_name}: {change}")
        for post_id, project_name, iri in unexpected:
            print(
                f"  UNEXPECTED {post_id} / {project_name}: {iri} "
                f"(neither namespace; left untouched)"
            )
        if unexpected:
            print(f"{len(unexpected)} row(s) carry an unrecognized namespace; nothing written")
            return 1
        if not planned:
            print("no legacy namespace rows remain")
            return 0
        if not apply:
            print(f"dry run: {len(planned)} row(s) would be rewritten; pass --apply to write")
            return 0

        async with conn.transaction():
            for post_id, project_name, change in planned:
                _old, _, new = change.rpartition(" -> ")
                updated = await conn.execute(
                    """
                    update post_project_mention
                    set ontology_iri = $3
                    where post_id = $1 and project_name = $2 and ontology_iri = $4
                    """,
                    post_id,
                    project_name,
                    new,
                    new.replace(CANONICAL_NAMESPACE, LEGACY_NAMESPACE),
                )
                if updated != "UPDATE 1":
                    raise RuntimeError(f"row changed during migration: {post_id}/{project_name}")
        print(f"applied: {len(planned)} row(s) rewritten to the canonical namespace")
        return 0
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="PostgreSQL DSN for the target database")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="execute the rewrite; without this flag the tool only reports",
    )
    args = parser.parse_args(argv)
    return __import__("asyncio").run(migrate(args.dsn, args.apply))


if __name__ == "__main__":
    sys.exit(main())
