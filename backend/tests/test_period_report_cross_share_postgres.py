"""PostgreSQL regression for primary-report cross-share JSON safety."""

from __future__ import annotations

import asyncio
import json
import math
import uuid

import asyncpg
import jwt
import psycopg2
import pytest

from backend.app.report_ingestion import fetch_period_reports
from backend.tests.test_api import seeded_db as _seeded_db_fixture
from scripts.seed_demo_data import _seed_demo_period_report

seeded_db = _seeded_db_fixture


@pytest.fixture(scope="module")
def demo_analyst_token() -> str:
    """Supply only the subject claim needed by the PostgreSQL seed fixture."""

    return jwt.encode({"sub": str(uuid.uuid4())}, key="", algorithm="none")


def test_fetch_period_reports_normalizes_persisted_nonfinite_cross_share(
    seeded_db,
) -> None:
    """PostgreSQL non-finite numerics become null while finite signs survive."""
    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) "
                "select corporate_entity_id, 'TEST-PU-FINITE-REPORT', 'Finite report unit' "
                "from source_post where post_id = %s returning process_unit_id",
                (seeded_db["own_private_post_id"],),
            )
            process_unit_id = cur.fetchone()[0]
            cur.execute(
                "select author_account_id, corporate_entity_id from source_post where post_id = %s",
                (seeded_db["own_private_post_id"],),
            )
            author_id, corp_id = cur.fetchone()
            _seed_demo_period_report(cur, author_id, corp_id, process_unit_id)
            cur.execute(
                "select grouping_kind, grouping_key, post_id, pair_kind "
                "from report_leftover_pair where period_code = '2026-W02' "
                "order by grouping_kind, grouping_key, pair_kind, post_id"
            )
            pair_rows = cur.fetchall()
            assert len(pair_rows) >= 7, pair_rows
            injected = [0.12, 0.0, -0.25, None, "NaN", "Infinity", "-Infinity"]
            for index, (kind, key, post_id, pair_kind) in enumerate(pair_rows):
                cur.execute(
                    "update report_leftover_pair set leftover_map_cross_share = %s "
                    "where grouping_kind = %s and grouping_key = %s "
                    "and period_code = '2026-W02' and pair_kind = %s and post_id = %s",
                    (injected[index % len(injected)], kind, key, pair_kind, post_id),
                )
    finally:
        admin_conn.close()

    async def _read_reports():
        conn = await asyncpg.connect(seeded_db["dsn"])
        try:
            return [
                await fetch_period_reports(conn, kind, "2026-W02")
                for kind in ("process_unit", "corporate_entity", "thread_group")
            ]
        finally:
            await conn.close()

    payloads = asyncio.run(_read_reports())
    shares = [
        pair["leftover_map_cross_share"]
        for payload in payloads
        for report in payload
        for pair in report["leftover_pairs"]
    ]
    assert shares
    assert all(share is None or math.isfinite(share) for share in shares)
    assert 0.12 in shares
    assert 0.0 in shares
    assert -0.25 in shares
    assert None in shares
    json.dumps(payloads, allow_nan=False)
