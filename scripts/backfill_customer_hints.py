"""Bounded operator backfill for evidence-backed customer-hint resolution.

This is intentionally an operator script, not a reader-facing HTTP route --
same shape as ``backfill_post_keymen.py``. It exists because
``resolve_customer_hint`` was previously reachable only one hint at a time
through the Customer Master "Resolve" button: a SAP-sourced import (e.g.
``public.zcrht811_export_rows``, whose only customer field is an opaque
SAP customer number with no name at all) can carry thousands of distinct
observed customer codes, so requiring an admin to click "Resolve" once per
code does not scale and leaves the overwhelming majority permanently
unresolved. This script reuses the exact same resolve-then-verify-then-
place pipeline (including corporate hierarchy inference) across a bounded
batch of still-unresolved codes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import Counter

import asyncpg

from backend.app.config import load_settings
from backend.app.customer_hint_ingestion import resolve_customer_hint
from backend.app.main import (
    _corporate_hierarchy_inference_client,
    _customer_hint_resolution_client,
    _relation_verification_client,
)
from lineageweave.http_client import HttpClientError


def _first_env(*names: str) -> str:
    return next((os.environ.get(name, "").strip() for name in names if os.environ.get(name, "").strip()), "")


def _orchestrator_config() -> tuple[str, str]:
    base_url = _first_env("ORCHESTRATOR_BASE_URL", "LLM_GATEWAY_API_URL", "LLM_GATEWAY_URL")
    api_key = _first_env("ORCHESTRATOR_API_KEY", "LLM_GATEWAY_API_KEY")
    if not base_url or not api_key:
        raise RuntimeError("contextual-orchestrator gateway configuration is unavailable")
    return base_url, api_key


async def _select_unresolved_hint_codes(
    conn: asyncpg.Connection, *, limit: int, hint_code: str | None
) -> list[str]:
    """One explicit hint code, or a bounded batch of still-unresolved ones.

    A hint code is "still unresolved" when at least one eligible post
    bearing it sits at its own account's default placeholder entity --
    the exact same predicate `resolve_customer_hint`'s own reclaim UPDATE
    uses, so this never re-selects a code every one of whose posts a
    prior resolution already reclaimed.
    """
    if hint_code:
        return [hint_code]
    rows = await conn.fetch(
        """
        select distinct post.source_customer_code as hint_code
          from source_post post
         where nullif(btrim(post.source_customer_code), '') is not null
           and nullif(btrim(post.source_draft_code), '') is null
           and nullif(btrim(post.source_deleted_flag), '') is null
           and not (
               (
                   nullif(btrim(post.source_author_code), '') is null
                   and nullif(btrim(post.source_author_name), '') is null
                   and nullif(btrim(post.source_company_code), '') is null
                   and nullif(btrim(post.source_company_name), '') is null
                   and nullif(btrim(post.source_process_unit_code), '') is null
                   and nullif(btrim(post.source_process_unit_name), '') is null
                   and nullif(btrim(post.source_sales_pool_code), '') is null
                   and nullif(btrim(post.source_sales_pool_name), '') is null
                   and nullif(btrim(post.source_customer_code), '') is null
                   and nullif(btrim(post.source_customer_name), '') is null
                   and nullif(btrim(post.source_project_code), '') is null
                   and nullif(btrim(post.source_project_name), '') is null
               )
               and exists (
                   select 1
                     from source_post real_post
                    where (
                        nullif(btrim(real_post.source_author_code), '') is not null
                        or nullif(btrim(real_post.source_author_name), '') is not null
                        or nullif(btrim(real_post.source_company_code), '') is not null
                        or nullif(btrim(real_post.source_company_name), '') is not null
                        or nullif(btrim(real_post.source_process_unit_code), '') is not null
                        or nullif(btrim(real_post.source_process_unit_name), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_code), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_name), '') is not null
                        or nullif(btrim(real_post.source_customer_code), '') is not null
                        or nullif(btrim(real_post.source_customer_name), '') is not null
                        or nullif(btrim(real_post.source_project_code), '') is not null
                        or nullif(btrim(real_post.source_project_name), '') is not null
                    )
               )
           )
           and post.corporate_entity_id in (
               select corporate_entity_id from account_affiliation
                where user_account_id = post.author_account_id
           )
         order by post.source_customer_code
         limit $1::bigint
        """,
        limit,
    )
    return [row["hint_code"] for row in rows]


async def _resolve_batch(
    conn: asyncpg.Connection,
    resolution_client: object,
    verification_client: object,
    hierarchy_client: object,
    hint_codes: list[str],
    hint_timeout: float,
) -> dict[str, object]:
    """Resolve each hint code in order, aggregating outcomes.

    Isolated from pool/connection setup so the aggregation itself (a
    declined resolution is not a failure; a timeout or provider error is
    counted but does not abort the remaining batch) is unit-testable
    without a real database or orchestrator.
    """
    failures: Counter[str] = Counter()
    declined = 0
    resolved: list[dict[str, object]] = []
    for hint_code in hint_codes:
        try:
            async with asyncio.timeout(hint_timeout):
                outcome = await resolve_customer_hint(
                    conn,
                    resolution_client,
                    verification_client,
                    hierarchy_client,
                    hint_code,
                )
            if outcome is None:
                declined += 1
            else:
                resolved.append({"hint_code": hint_code, **outcome})
        except TimeoutError:
            failures["TimeoutError"] += 1
        except (HttpClientError, OSError, RuntimeError, ValueError, asyncpg.PostgresError) as exc:
            failures[type(exc).__name__] += 1
    return {
        "requested_hint_codes": len(hint_codes),
        "resolved_hint_codes": len(resolved),
        "declined_hint_codes": declined,
        "linked_post_count": sum(int(entry["linked_post_count"]) for entry in resolved),
        "resolved": resolved,
        "failed_hint_codes": sum(failures.values()),
        "failure_types": dict(sorted(failures.items())),
    }


async def _run(args: argparse.Namespace) -> dict[str, object]:
    if args.hint_code and args.all:
        raise ValueError("--hint-code and --all cannot be combined")
    # The resolution channel itself must be configured; hierarchy inference
    # and verification are separately optional -- resolve_customer_hint
    # falls back to a flat entity when they decline, same as its own
    # single-hint API route already does.
    _orchestrator_config()
    settings = load_settings()
    resolution_client = _customer_hint_resolution_client()
    verification_client = _relation_verification_client()
    hierarchy_client = _corporate_hierarchy_inference_client()
    limit = 1 if args.hint_code or not args.all else args.limit

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=1)
    try:
        async with pool.acquire() as conn:
            hint_codes = await _select_unresolved_hint_codes(conn, limit=limit, hint_code=args.hint_code)
            return await _resolve_batch(
                conn, resolution_client, verification_client, hierarchy_client, hint_codes, args.hint_timeout
            )
    finally:
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--hint-code", help="Re-resolve one explicit source_customer_code")
    selector.add_argument("--all", action="store_true", help="Process the explicit --limit batch")
    parser.add_argument("--limit", type=int, default=25, help="Maximum hint codes for --all (default: 25)")
    parser.add_argument(
        "--hint-timeout",
        type=float,
        default=120.0,
        help="Maximum seconds per hint code including provider calls (default: 120)",
    )
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.hint_timeout <= 0:
        parser.error("--hint-timeout must be positive")
    print(json.dumps(asyncio.run(_run(args)), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
