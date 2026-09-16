"""Queued llm-inclusive channel-weight estimation (ADR 0200 point 5).

Bulk synchronous provider calls are banned (operator directive,
2026-08-24), so the llm channel is scored through
contextual-orchestrator's durable batch routing API instead:

``submit``
    samples candidate pairs exactly as the deterministic estimator does,
    takes a bounded deterministic stride subsample, submits ONE batch
    routing job (one request per pair, ``custom_id=pair-<ordinal>``),
    and persists the run plus every pair's deterministic scores into
    ``lineage_weight_estimation_run`` / ``lineage_pair_judgment``
    (migration 0201). It never waits on the provider.

``collect``
    polls the batch job once; when complete it retrieves the results,
    maps each score back to its pair by ``custom_id`` (caller-supplied
    ids landed upstream for exactly this — contextual-orchestrator
    #832), persists per-pair llm scores durably, and only when the run
    is complete fits the 4-channel expected-information estimate and
    persists it as the ``channel_set_with_llm`` set with full
    provenance. Killed mid-collect, nothing is lost: re-run ``collect``.

Persisting is not activating: the product loader refuses every anchor
method until one is authorized under ADR 0200 point 3.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone

import asyncpg

from backend.app.config import load_settings
from backend.app.lineage_ingestion import records_from_source_posts
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.adjudication_client import judge_prompt, parse_confidence_or_none
from lineageweave.channel_weight_estimation import estimate_channel_weights
from lineageweave.http_client import get_json, post_json

from scripts.estimate_channel_weights import (
    persist_estimate,
    sample_pair_scores,
    source_snapshot_digest,
    subsample_stride,
)

WITH_LLM_SET_CODE = "channel_set_with_llm"
_BATCH_TIMEOUT_SECONDS = 60.0


def _orchestrator_config() -> tuple[str, str]:
    """Return the published contextual-orchestrator consumer endpoint and bearer."""
    base_url = os.environ.get("ORCHESTRATOR_BASE_URL", "").strip()
    api_key = os.environ.get("ORCHESTRATOR_API_KEY", "").strip()
    if not base_url or not api_key:
        raise RuntimeError(
            "set ORCHESTRATOR_BASE_URL and ORCHESTRATOR_API_KEY to reach "
            "the contextual-orchestrator batch routing API"
        )
    return base_url.rstrip("/"), api_key


def batch_requests_for_pairs(
    chosen: list[int], pair_labels: list[tuple[str, str]]
) -> list[dict[str, object]]:
    """One batch request per chosen pair, keyed by its ordinal.

    Every request carries a caller-supplied ``custom_id`` and none rely
    on the server-generated ids, so results map back to pairs on any
    backend regardless of result ordering (and per upstream guidance,
    caller and generated ids are never mixed within one batch).
    """
    return [
        {
            "custom_id": f"pair-{ordinal}",
            "mode": "auto",
            "messages": [
                {
                    "role": "user",
                    "content": judge_prompt(*pair_labels[ordinal]),
                }
            ],
        }
        for ordinal in chosen
    ]


async def _submit(args: argparse.Namespace) -> dict[str, object]:
    """Sample, submit one batch job, persist the run ledger. Never waits."""
    base_url, api_key = _orchestrator_config()
    settings = load_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        rows = await conn.fetch(
            "select post_id, post_title, voc_type_code, created_at, "
            "corporate_entity_id, process_unit_id, thread_group_key, "
            "secondary_grouping_key "
            f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')} "
            "order by created_at, post_id limit $1::bigint",
            args.post_limit,
        )
    finally:
        await conn.close()
    if not rows:
        raise RuntimeError(
            "no eligible source posts exist; import a corpus before estimating"
        )
    snapshot_sha256 = source_snapshot_digest(rows)
    knowledge_cutoff = max(row["created_at"] for row in rows)
    pair_scores, group_ids, pair_labels = sample_pair_scores(
        records_from_source_posts(rows)
    )
    chosen = subsample_stride(len(pair_scores), args.pair_limit)
    if not chosen:
        raise RuntimeError("the corpus produced no candidate pairs to judge")

    submitted = post_json(
        f"{base_url}/api/v1/batch_routing_jobs",
        {"requests": batch_requests_for_pairs(chosen, pair_labels)},
        headers={"authorization": f"Bearer {api_key}"},
        timeout=_BATCH_TIMEOUT_SECONDS,
    )
    batch_job_id = str(submitted["job_id"])

    conn = await asyncpg.connect(settings.database_url)
    try:
        async with conn.transaction():
            estimation_run_id = await conn.fetchval(
                """
                insert into lineage_weight_estimation_run
                    (estimation_run_id, channel_set_code, run_status_code,
                     batch_job_id, source_snapshot_sha256, knowledge_cutoff,
                     sampled_pair_count)
                values (gen_random_uuid(), $1, 'run_submitted', $2, $3, $4, $5)
                returning estimation_run_id
                """,
                WITH_LLM_SET_CODE,
                batch_job_id,
                snapshot_sha256,
                knowledge_cutoff,
                len(chosen),
            )
            for ordinal in chosen:
                scores = pair_scores[ordinal]
                candidate_label, record_label = pair_labels[ordinal]
                await conn.execute(
                    """
                    insert into lineage_pair_judgment
                        (estimation_run_id, pair_ordinal, group_ordinal,
                         candidate_label, record_label, temporal_score,
                         secondary_key_score, text_score)
                    values ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    estimation_run_id,
                    ordinal,
                    group_ids[ordinal],
                    candidate_label,
                    record_label,
                    scores["temporal"],
                    scores["secondary_key"],
                    scores["text"],
                )
    except Exception as exc:
        raise RuntimeError(
            f"batch job {batch_job_id} was submitted but the run ledger "
            "could not be persisted; re-run submit (the orphaned job only "
            "costs its provider spend, no state references it)"
        ) from exc
    finally:
        await conn.close()
    return {
        "estimation_run_id": str(estimation_run_id),
        "batch_job_id": batch_job_id,
        "sampled_pair_count": len(chosen),
        "next_action": "run collect once the batch job completes",
    }


def _is_complete(polled: dict[str, object]) -> bool:
    """True when the batch backend reports a terminal successful state."""
    if polled.get("is_complete") is True:
        return True
    return str(polled.get("status", "")).lower() in {"completed", "succeeded"}


def judgment_updates_from_results(
    results: list[dict[str, object]],
) -> list[tuple[int, float]]:
    """Map batch results onto (pair_ordinal, llm_score) updates.

    Mapping is by caller-supplied ``custom_id`` only -- never result
    order. An unparseable or empty answer is OMITTED, not stored: an
    errored request must stay unjudged rather than become a confident
    0.0 ("definitely unrelated") verdict the judge never gave.
    """
    updates: list[tuple[int, float]] = []
    for item in results:
        custom_id = str(item.get("custom_id", ""))
        if not custom_id.startswith("pair-"):
            continue
        try:
            ordinal = int(custom_id.removeprefix("pair-"))
        except ValueError:
            continue
        score = parse_confidence_or_none(str(item.get("answer", "")))
        if score is None:
            continue
        updates.append((ordinal, score))
    return updates


async def _collect(args: argparse.Namespace) -> dict[str, object]:
    """Collect one completed batch into the ledger; fit when the run is whole.

    No database connection is held across the HTTP calls or the model
    fit (an idle-reaped connection killed an earlier estimation run):
    each phase opens its own short-lived connection.
    """
    base_url, api_key = _orchestrator_config()
    settings = load_settings()

    conn = await asyncpg.connect(settings.database_url)
    try:
        if args.run_id:
            run = await conn.fetchrow(
                """
                select estimation_run_id, batch_job_id, run_status_code,
                       source_snapshot_sha256, knowledge_cutoff, sampled_pair_count
                from lineage_weight_estimation_run
                where estimation_run_id = $1::uuid
                  and run_status_code in ('run_submitted', 'run_collecting')
                """,
                args.run_id,
            )
        else:
            run = await conn.fetchrow(
                """
                select estimation_run_id, batch_job_id, run_status_code,
                       source_snapshot_sha256, knowledge_cutoff, sampled_pair_count
                from lineage_weight_estimation_run
                where run_status_code in ('run_submitted', 'run_collecting')
                order by requested_at desc
                limit 1
                """
            )
    finally:
        await conn.close()
    if run is None:
        raise RuntimeError(
            "no submitted run awaits collection; run submit first "
            "(or pass --run-id for an older run)"
        )

    polled = get_json(
        f"{base_url}/api/v1/batch_routing_jobs/{run['batch_job_id']}",
        headers={"authorization": f"Bearer {api_key}"},
        timeout=_BATCH_TIMEOUT_SECONDS,
        service_peer_name="contextual-orchestrator",
    )
    if not _is_complete(polled):
        return {
            "estimation_run_id": str(run["estimation_run_id"]),
            "batch_job_id": run["batch_job_id"],
            "batch_status": polled.get("status"),
            "next_action": "batch not complete yet; run collect again later",
        }

    retrieved = post_json(
        f"{base_url}/api/v1/batch_routing_jobs/{run['batch_job_id']}/results",
        {},
        headers={"authorization": f"Bearer {api_key}"},
        timeout=_BATCH_TIMEOUT_SECONDS,
    )
    updates = judgment_updates_from_results(retrieved.get("results", []))
    judged_at = datetime.now(timezone.utc)

    conn = await asyncpg.connect(settings.database_url)
    try:
        async with conn.transaction():
            for ordinal, score in updates:
                await conn.execute(
                    """
                    update lineage_pair_judgment
                    set llm_score = $3, judged_at = $4
                    where estimation_run_id = $1 and pair_ordinal = $2
                    """,
                    run["estimation_run_id"],
                    ordinal,
                    score,
                    judged_at,
                )
            await conn.execute(
                """
                update lineage_weight_estimation_run
                set run_status_code = 'run_collecting',
                    judged_pair_count = (
                        select count(*) from lineage_pair_judgment
                        where estimation_run_id = $1 and llm_score is not null
                    )
                where estimation_run_id = $1
                """,
                run["estimation_run_id"],
            )
        pairs = await conn.fetch(
            """
            select group_ordinal, temporal_score, secondary_key_score,
                   text_score, llm_score
            from lineage_pair_judgment
            where estimation_run_id = $1
            order by pair_ordinal
            """,
            run["estimation_run_id"],
        )
    finally:
        await conn.close()

    unjudged = sum(1 for row in pairs if row["llm_score"] is None)
    if unjudged:
        return {
            "estimation_run_id": str(run["estimation_run_id"]),
            "judged_pair_count": len(pairs) - unjudged,
            "sampled_pair_count": len(pairs),
            "next_action": (
                f"{unjudged} pairs have no parseable judgment yet; run "
                "collect again once the batch delivers them, or re-submit "
                "if the provider errored them permanently"
            ),
        }

    # The fit can take minutes; no connection is open while it runs.
    estimate = estimate_channel_weights(
        [
            {
                "temporal": row["temporal_score"],
                "secondary_key": row["secondary_key_score"],
                "text": row["text_score"],
                "llm": row["llm_score"],
            }
            for row in pairs
        ],
        [int(row["group_ordinal"]) for row in pairs],
    )

    conn = await asyncpg.connect(settings.database_url)
    try:
        if estimate is None:
            await conn.execute(
                "update lineage_weight_estimation_run "
                "set run_status_code = 'run_failed', completed_at = now() "
                "where estimation_run_id = $1",
                run["estimation_run_id"],
            )
            raise RuntimeError(
                "no grounded estimate was produced over the judged pairs "
                "(fast_mlsirm unavailable, sample too small, a channel "
                "degenerate, or the fit did not converge) -- the run is "
                "marked run_failed; nothing was written to the weight table"
            )
        await persist_estimate(
            conn,
            estimate,
            channel_set_code=WITH_LLM_SET_CODE,
            snapshot_sha256=run["source_snapshot_sha256"],
            knowledge_cutoff=run["knowledge_cutoff"],
        )
        await conn.execute(
            "update lineage_weight_estimation_run "
            "set run_status_code = 'run_fitted', completed_at = now() "
            "where estimation_run_id = $1",
            run["estimation_run_id"],
        )
    finally:
        await conn.close()
    return {
        "estimation_run_id": str(run["estimation_run_id"]),
        "weights": estimate.weights,
        "channel_set_code": WITH_LLM_SET_CODE,
        "sample_pair_count": estimate.sample_pair_count,
        "estimation_method_code": estimate.estimation_method_code,
        "activation": (
            "blocked_until_anchor_authorized (ADR 0200 point 3): the "
            "product loader refuses every anchor method today"
        ),
    }


def main() -> None:
    """Validate operator inputs and run the chosen phase."""
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="phase", required=True)
    submit = subcommands.add_parser("submit", help="sample pairs and submit one batch job")
    submit.add_argument("--post-limit", type=int, default=5000)
    submit.add_argument("--pair-limit", type=int, default=400)
    collect = subcommands.add_parser(
        "collect", help="collect results; fit when the run is whole"
    )
    collect.add_argument(
        "--run-id",
        default="",
        help="collect a specific estimation run (default: the newest awaiting one)",
    )
    args = parser.parse_args()
    if args.phase == "submit":
        if args.post_limit < 1:
            parser.error("--post-limit must be positive")
        if args.pair_limit < 1:
            parser.error("--pair-limit must be positive")
        result = asyncio.run(_submit(args))
    else:
        result = asyncio.run(_collect(args))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
