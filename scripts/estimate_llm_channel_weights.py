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
    orchestrator_base_url = os.environ.get("ORCHESTRATOR_BASE_URL", "").strip()
    orchestrator_api_key = os.environ.get("ORCHESTRATOR_API_KEY", "").strip()
    if not orchestrator_base_url or not orchestrator_api_key:
        raise RuntimeError(
            "set ORCHESTRATOR_BASE_URL and ORCHESTRATOR_API_KEY to reach "
            "the contextual-orchestrator batch routing API"
        )
    return orchestrator_base_url.rstrip("/"), orchestrator_api_key


def batch_requests_for_pairs(
    chosen_pair_ordinals: list[int], candidate_pair_labels: list[tuple[str, str]]
) -> list[dict[str, object]]:
    """One batch request per chosen pair, keyed by its ordinal.

    Every request carries a caller-supplied ``custom_id`` and none rely
    on the server-generated ids, so results map back to pairs on any
    backend regardless of result ordering (and per upstream guidance,
    caller and generated ids are never mixed within one batch).
    """
    return [
        {
            "custom_id": f"pair-{pair_ordinal}",
            "mode": "auto",
            "messages": [
                {
                    "role": "user",
                    "content": judge_prompt(*candidate_pair_labels[pair_ordinal]),
                }
            ],
        }
        for pair_ordinal in chosen_pair_ordinals
    ]


async def _submit_batch_estimation(
    command_arguments: argparse.Namespace,
) -> dict[str, object]:
    """Sample, submit one batch job, persist the run ledger. Never waits."""
    orchestrator_base_url, orchestrator_api_key = _orchestrator_config()
    runtime_settings = load_settings()
    database_connection = await asyncpg.connect(runtime_settings.database_url)
    try:
        source_post_rows = await database_connection.fetch(
            "select post_id, post_title, voc_type_code, created_at, "
            "corporate_entity_id, process_unit_id, thread_group_key, "
            "secondary_grouping_key "
            f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')} "
            "order by created_at, post_id limit $1::bigint",
            command_arguments.post_limit,
        )
    finally:
        await database_connection.close()
    if not source_post_rows:
        raise RuntimeError(
            "no eligible source posts exist; import a corpus before estimating"
        )
    source_snapshot_sha256 = source_snapshot_digest(source_post_rows)
    knowledge_cutoff = max(
        source_post_row["created_at"] for source_post_row in source_post_rows
    )
    candidate_pair_scores, reconstruction_group_ids, candidate_pair_labels = (
        sample_pair_scores(records_from_source_posts(source_post_rows))
    )
    chosen_pair_ordinals = subsample_stride(
        len(candidate_pair_scores), command_arguments.pair_limit
    )
    if not chosen_pair_ordinals:
        raise RuntimeError("the corpus produced no candidate pairs to judge")

    batch_submission = post_json(
        f"{orchestrator_base_url}/api/v1/batch_routing_jobs",
        {
            "requests": batch_requests_for_pairs(
                chosen_pair_ordinals, candidate_pair_labels
            )
        },
        headers={"authorization": f"Bearer {orchestrator_api_key}"},
        timeout=_BATCH_TIMEOUT_SECONDS,
    )
    batch_job_id = str(batch_submission["job_id"])

    database_connection = await asyncpg.connect(runtime_settings.database_url)
    try:
        async with database_connection.transaction():
            estimation_run_id = await database_connection.fetchval(
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
                source_snapshot_sha256,
                knowledge_cutoff,
                len(chosen_pair_ordinals),
            )
            for pair_ordinal in chosen_pair_ordinals:
                channel_scores = candidate_pair_scores[pair_ordinal]
                candidate_label, record_label = candidate_pair_labels[pair_ordinal]
                await database_connection.execute(
                    """
                    insert into lineage_pair_judgment
                        (estimation_run_id, pair_ordinal, group_ordinal,
                         candidate_label, record_label, temporal_score,
                         secondary_key_score, text_score)
                    values ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    estimation_run_id,
                    pair_ordinal,
                    reconstruction_group_ids[pair_ordinal],
                    candidate_label,
                    record_label,
                    channel_scores["temporal"],
                    channel_scores["secondary_key"],
                    channel_scores["text"],
                )
    except Exception as submission_error:
        raise RuntimeError(
            f"batch job {batch_job_id} was submitted but the run ledger "
            "could not be persisted; re-run submit (the orphaned job only "
            "costs its provider spend, no state references it)"
        ) from submission_error
    finally:
        await database_connection.close()
    return {
        "estimation_run_id": str(estimation_run_id),
        "batch_job_id": batch_job_id,
        "sampled_pair_count": len(chosen_pair_ordinals),
        "next_action": "run collect once the batch job completes",
    }


def _is_complete(batch_status_payload: dict[str, object]) -> bool:
    """True when the batch backend reports a terminal successful state."""
    if batch_status_payload.get("is_complete") is True:
        return True
    return str(batch_status_payload.get("status", "")).lower() in {
        "completed",
        "succeeded",
    }


def judgment_updates_from_results(
    batch_result_records: list[dict[str, object]],
) -> list[tuple[int, float]]:
    """Map batch results onto (pair_ordinal, llm_score) updates.

    Mapping is by caller-supplied ``custom_id`` only -- never result
    order. An unparseable or empty answer is OMITTED, not stored: an
    errored request must stay unjudged rather than become a confident
    0.0 ("definitely unrelated") verdict the judge never gave.
    """
    judgment_updates: list[tuple[int, float]] = []
    for batch_result_record in batch_result_records:
        custom_id = str(batch_result_record.get("custom_id", ""))
        if not custom_id.startswith("pair-"):
            continue
        try:
            pair_ordinal = int(custom_id.removeprefix("pair-"))
        except ValueError:
            continue
        llm_score = parse_confidence_or_none(str(batch_result_record.get("answer", "")))
        if llm_score is None:
            continue
        judgment_updates.append((pair_ordinal, llm_score))
    return judgment_updates


async def _collect_batch_estimation(
    command_arguments: argparse.Namespace,
) -> dict[str, object]:
    """Collect one completed batch into the ledger; fit when the run is whole.

    No database connection is held across the HTTP calls or the model
    fit (an idle-reaped connection killed an earlier estimation run):
    each phase opens its own short-lived connection.
    """
    orchestrator_base_url, orchestrator_api_key = _orchestrator_config()
    runtime_settings = load_settings()

    database_connection = await asyncpg.connect(runtime_settings.database_url)
    try:
        if command_arguments.run_id:
            estimation_run_record = await database_connection.fetchrow(
                """
                select estimation_run_id, batch_job_id, run_status_code,
                       source_snapshot_sha256, knowledge_cutoff, sampled_pair_count
                from lineage_weight_estimation_run
                where estimation_run_id = $1::uuid
                  and run_status_code in ('run_submitted', 'run_collecting')
                """,
                command_arguments.run_id,
            )
        else:
            estimation_run_record = await database_connection.fetchrow(
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
        await database_connection.close()
    if estimation_run_record is None:
        raise RuntimeError(
            "no submitted run awaits collection; run submit first "
            "(or pass --run-id for an older run)"
        )

    batch_status_payload = get_json(
        f"{orchestrator_base_url}/api/v1/batch_routing_jobs/"
        f"{estimation_run_record['batch_job_id']}",
        headers={"authorization": f"Bearer {orchestrator_api_key}"},
        timeout=_BATCH_TIMEOUT_SECONDS,
        service_peer_name="contextual-orchestrator",
    )
    if not _is_complete(batch_status_payload):
        return {
            "estimation_run_id": str(estimation_run_record["estimation_run_id"]),
            "batch_job_id": estimation_run_record["batch_job_id"],
            "batch_status": batch_status_payload.get("status"),
            "next_action": "batch not complete yet; run collect again later",
        }

    batch_results_payload = post_json(
        f"{orchestrator_base_url}/api/v1/batch_routing_jobs/"
        f"{estimation_run_record['batch_job_id']}/results",
        {},
        headers={"authorization": f"Bearer {orchestrator_api_key}"},
        timeout=_BATCH_TIMEOUT_SECONDS,
    )
    judgment_updates = judgment_updates_from_results(
        batch_results_payload.get("results", [])
    )
    judged_at = datetime.now(timezone.utc)

    database_connection = await asyncpg.connect(runtime_settings.database_url)
    try:
        async with database_connection.transaction():
            for pair_ordinal, llm_score in judgment_updates:
                await database_connection.execute(
                    """
                    update lineage_pair_judgment
                    set llm_score = $3, judged_at = $4
                    where estimation_run_id = $1 and pair_ordinal = $2
                    """,
                    estimation_run_record["estimation_run_id"],
                    pair_ordinal,
                    llm_score,
                    judged_at,
                )
            await database_connection.execute(
                """
                update lineage_weight_estimation_run
                set run_status_code = 'run_collecting',
                    judged_pair_count = (
                        select count(*) from lineage_pair_judgment
                        where estimation_run_id = $1 and llm_score is not null
                    )
                where estimation_run_id = $1
                """,
                estimation_run_record["estimation_run_id"],
            )
        pair_judgment_records = await database_connection.fetch(
            """
            select group_ordinal, temporal_score, secondary_key_score,
                   text_score, llm_score
            from lineage_pair_judgment
            where estimation_run_id = $1
            order by pair_ordinal
            """,
            estimation_run_record["estimation_run_id"],
        )
    finally:
        await database_connection.close()

    unjudged_pair_count = sum(
        1
        for pair_judgment_record in pair_judgment_records
        if pair_judgment_record["llm_score"] is None
    )
    if unjudged_pair_count:
        return {
            "estimation_run_id": str(estimation_run_record["estimation_run_id"]),
            "judged_pair_count": len(pair_judgment_records) - unjudged_pair_count,
            "sampled_pair_count": len(pair_judgment_records),
            "next_action": (
                f"{unjudged_pair_count} pairs have no parseable judgment yet; run "
                "collect again once the batch delivers them, or re-submit "
                "if the provider errored them permanently"
            ),
        }

    # The fit can take minutes; no connection is open while it runs.
    channel_weight_estimate = estimate_channel_weights(
        [
            {
                "temporal": pair_judgment_record["temporal_score"],
                "secondary_key": pair_judgment_record["secondary_key_score"],
                "text": pair_judgment_record["text_score"],
                "llm": pair_judgment_record["llm_score"],
            }
            for pair_judgment_record in pair_judgment_records
        ],
        [
            int(pair_judgment_record["group_ordinal"])
            for pair_judgment_record in pair_judgment_records
        ],
    )

    database_connection = await asyncpg.connect(runtime_settings.database_url)
    try:
        if channel_weight_estimate is None:
            await database_connection.execute(
                "update lineage_weight_estimation_run "
                "set run_status_code = 'run_failed', completed_at = now() "
                "where estimation_run_id = $1",
                estimation_run_record["estimation_run_id"],
            )
            raise RuntimeError(
                "no grounded estimate was produced over the judged pairs "
                "(fast_mlsirm unavailable, sample too small, a channel "
                "degenerate, or the fit did not converge) -- the run is "
                "marked run_failed; nothing was written to the weight table"
            )
        await persist_estimate(
            database_connection,
            channel_weight_estimate,
            channel_set_code=WITH_LLM_SET_CODE,
            snapshot_sha256=estimation_run_record["source_snapshot_sha256"],
            knowledge_cutoff=estimation_run_record["knowledge_cutoff"],
        )
        await database_connection.execute(
            "update lineage_weight_estimation_run "
            "set run_status_code = 'run_fitted', completed_at = now() "
            "where estimation_run_id = $1",
            estimation_run_record["estimation_run_id"],
        )
    finally:
        await database_connection.close()
    return {
        "estimation_run_id": str(estimation_run_record["estimation_run_id"]),
        "weights": channel_weight_estimate.weights,
        "channel_set_code": WITH_LLM_SET_CODE,
        "sample_pair_count": channel_weight_estimate.sample_pair_count,
        "estimation_method_code": channel_weight_estimate.estimation_method_code,
        "activation": (
            "blocked_until_anchor_authorized (ADR 0200 point 3): the "
            "product loader refuses every anchor method today"
        ),
    }


def main() -> None:
    """Validate operator inputs and run the chosen phase."""
    argument_parser = argparse.ArgumentParser(description=__doc__)
    phase_subparsers = argument_parser.add_subparsers(dest="phase", required=True)
    submit_parser = phase_subparsers.add_parser(
        "submit", help="sample pairs and submit one batch job"
    )
    submit_parser.add_argument("--post-limit", type=int, default=5000)
    submit_parser.add_argument("--pair-limit", type=int, default=400)
    collect_parser = phase_subparsers.add_parser(
        "collect", help="collect results; fit when the run is whole"
    )
    collect_parser.add_argument(
        "--run-id",
        default="",
        help="collect a specific estimation run (default: the newest awaiting one)",
    )
    command_arguments = argument_parser.parse_args()
    if command_arguments.phase == "submit":
        if command_arguments.post_limit < 1:
            argument_parser.error("--post-limit must be positive")
        if command_arguments.pair_limit < 1:
            argument_parser.error("--pair-limit must be positive")
        command_result = asyncio.run(_submit_batch_estimation(command_arguments))
    else:
        command_result = asyncio.run(_collect_batch_estimation(command_arguments))
    print(json.dumps(command_result, ensure_ascii=False, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
