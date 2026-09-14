"""Backfill for the dataset-wide Event Lineage grouping-key placeholders.

The whole reason `lineageweave.reconstruct` exists is that the source
system carries no reliable thread key at all -- related posts arrive
unlinked, and lineage is *reconstructed* from evidence: the temporal,
secondary-key, text-similarity, and llm channels fused through RankWeave
(see reconstruct.py's own validation note: naive grouping-plus-recency
agreed with an independent signal only 2.6% of the time). `group_key`
is therefore only the candidate-pool bound; the channels decide the
actual links.

An authorized-source validation found that an import had inverted that design
by putting per-row identity values into both grouping columns. That produced
singleton candidate pools, while the secondary-key channel could not fire.
Only this aggregate failure mode is retained here; private source identifiers
and records remain outside repository artifacts.

Event Lineage, the product's headline feature, was silently
non-functional for virtually the whole corpus. This backfill restores
the library's designed inputs, only on rows carrying the placeholder
signature (`thread_group_key` equal to the row's own
`source_record_key`) so seeded demo rows with real designed keys are
untouched:

1. `thread_group_key` -> `''` (the column is NOT NULL; migration 0002
   made the empty string the "no persisted signal" value), so
   `reconstruct_group_key`'s existing fallback to
   `process_unit_id`/`corporate_entity_id` forms real candidate pools.
2. `secondary_grouping_key` -> `source_project_code` (empty where the
   source had none), so posts naming the same project contribute
   fused *evidence* toward a link without being walled off from
   related posts that lack a project code -- a hard project partition
   on `thread_group_key` would have blocked exactly the
   high-relatedness cross-links this library exists to find.

Idempotent and safe to re-run. Does not itself rebuild
`post_lineage_edge` -- run `POST /api/lineage/rebuild` (or the
equivalent `rebuild_lineage()` call) afterward.

`thread_group_key` is not lineage-only: it is also the live scope key
for `analysis_scope_thread_group` analysis runs (TEPP measurement and
period reports included -- `analysis_run_ingestion.py` re-resolves
`p.thread_group_key = scope.scope_key` on every read for
ABAC-visibility, and `report_ingestion.py` groups thread-group reports
by it). A run's *member posts* are frozen in
`analysis_source_snapshot_member` at capture time, but that live scope
match is not. Rewriting keys would therefore orphan any existing
thread-group-scoped run: this script fails closed if one exists whose
`scope_key` still matches a current `thread_group_key`, rather than
silently detaching it.
"""

from __future__ import annotations

import argparse
import asyncio
import json

import asyncpg

from backend.app.config import load_settings


async def backfill_thread_group_keys(
    database_connection: asyncpg.Connection, *, dry_run: bool
) -> dict[str, int]:
    """Clear placeholder grouping keys and route project codes to the
    secondary-key channel.

    Isolated from pool/connection setup so the counting/rollback logic is
    unit-testable without a real database. Fails closed (no write) when an
    existing `analysis_scope_thread_group` run's scope_key would be
    orphaned by the rewrite -- that run's ABAC-visibility scope match is
    resolved live against `thread_group_key` on every read, not frozen in
    its snapshot.
    """
    async with database_connection.transaction():
        anchored_analysis_runs = await database_connection.fetch(
            """
            select scope.analysis_run_id, scope.scope_key
              from analysis_run_scope scope
             where scope.scope_kind_code = 'analysis_scope_thread_group'
               and exists (
                   select 1 from source_post p
                    where btrim(p.thread_group_key) = scope.scope_key
                      and btrim(p.thread_group_key) = btrim(p.source_record_key)
               )
            """
        )
        if anchored_analysis_runs:
            analysis_run_ids = ", ".join(
                str(anchored_run["analysis_run_id"])
                for anchored_run in anchored_analysis_runs
            )
            raise RuntimeError(
                "refusing to rewrite thread_group_key: existing "
                f"analysis_scope_thread_group run(s) [{analysis_run_ids}] resolve their "
                "scope against values this backfill would change. Retire or "
                "re-scope those runs first."
            )
        # Only rows carrying the placeholder signature -- a thread key equal
        # to the row's own record key groups nothing and can only be import
        # damage; a seeded or genuinely-mapped key never self-references.
        updated_post_records = await database_connection.fetch(
            """
            update source_post
               set source_thread_group_key = coalesce(
                       source_thread_group_key, thread_group_key
                   ),
                   source_secondary_grouping_key = coalesce(
                       source_secondary_grouping_key, secondary_grouping_key
                   ),
                   thread_group_key = '',
                   secondary_grouping_key = coalesce(nullif(btrim(source_project_code), ''), '')
             where source_record_key is not null
               and btrim(thread_group_key) = btrim(source_record_key)
            returning (nullif(btrim(source_project_code), '') is not null) as had_project_code
            """
        )
        project_evidence_post_count = sum(
            1
            for updated_post_record in updated_post_records
            if updated_post_record["had_project_code"]
        )
        cleared_post_count = len(updated_post_records)
        if dry_run:
            raise _RollbackDryRun(
                project_evidence_post_count,
                cleared_post_count,
            )
    return {
        "cleared_placeholder_posts": cleared_post_count,
        "project_secondary_evidence_posts": project_evidence_post_count,
    }


class _RollbackDryRun(Exception):
    """Raised inside the transaction to force a rollback for --dry-run."""

    def __init__(
        self,
        project_evidence_post_count: int,
        cleared_post_count: int,
    ) -> None:
        """Retain the aggregate counts that the rolled-back operator run reports."""
        super().__init__("dry run -- rolled back")
        self.project_evidence_post_count = project_evidence_post_count
        self.cleared_post_count = cleared_post_count


async def _run_thread_group_key_backfill(
    command_arguments: argparse.Namespace,
) -> dict[str, object]:
    """Execute one pooled backfill and convert dry-run rollback into counts."""
    runtime_settings = load_settings()
    database_pool = await asyncpg.create_pool(
        runtime_settings.database_url, min_size=1, max_size=1
    )
    try:
        async with database_pool.acquire() as database_connection:
            try:
                backfill_counts = await backfill_thread_group_keys(
                    database_connection,
                    dry_run=command_arguments.dry_run,
                )
                return {**backfill_counts, "dry_run": False}
            except _RollbackDryRun as rolled_back:
                return {
                    "cleared_placeholder_posts": rolled_back.cleared_post_count,
                    "project_secondary_evidence_posts": (
                        rolled_back.project_evidence_post_count
                    ),
                    "dry_run": True,
                }
    finally:
        await database_pool.close()


def main() -> None:
    """Parse operator arguments and print aggregate, non-identifying evidence."""
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report counts without writing (rolls back the transaction)",
    )
    command_arguments = argument_parser.parse_args()
    print(
        json.dumps(
            asyncio.run(_run_thread_group_key_backfill(command_arguments)),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
