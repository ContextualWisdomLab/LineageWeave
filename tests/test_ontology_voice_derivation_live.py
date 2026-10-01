"""PostgreSQL regressions for qualified Voice derivation admission (ADR 0256)."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta

import asyncpg
import pytest

from backend.app.ontology_neighborhood_ingestion import _load_voice_assignments


def test_voice_projection_requires_derivation_and_visible_evidence() -> None:
    """An unrelated PROV relation cannot become an additional Voice claim."""
    asyncio.run(_check_voice_projection())


async def _check_voice_projection() -> None:
    dsn = os.environ.get(
        "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN",
        "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
    )
    try:
        conn = await asyncpg.connect(dsn, timeout=3)
    except (OSError, asyncpg.PostgresError, TimeoutError):
        pytest.skip("requires a reachable authorized PostgreSQL test connection")
    post_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
    evidence_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"
    recorded = datetime(2026, 1, 10, tzinfo=UTC)
    try:
        # Session-local tables shadow the product tables without reading or
        # changing runtime records; connection close removes every fixture.
        await conn.execute("""
            create temp table common_lookup_value (
                lookup_category text, lookup_code text,
                lookup_label text, display_order integer
            );
            create temp table source_post_voice (
                post_id uuid, voice_type_code text, is_primary boolean,
                truth_status_code text, recorded_at timestamptz,
                effective_from timestamptz, effective_to timestamptz,
                provenance_assertion_id uuid
            );
            create temp table provenance_assertion (
                assertion_id uuid, object_resource_id uuid, relation_code text
            );
            create temp table provenance_resource_binding (
                resource_id uuid, node_type_code text, node_id uuid
            );
            insert into common_lookup_value values
                ('voc_type', 'voc', 'Voice of Customer', 1),
                ('voc_type', 'vops', 'Voice of Process', 2),
                ('voc_type', 'voe', 'Voice of Employee', 3);
            insert into provenance_assertion values
                ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1',
                 'cccccccc-cccc-cccc-cccc-ccccccccccc1', 'prov_was_derived_from'),
                ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2',
                 'cccccccc-cccc-cccc-cccc-ccccccccccc1', 'prov_was_influenced_by');
        """)
        await conn.execute(
            "insert into provenance_resource_binding values "
            "('cccccccc-cccc-cccc-cccc-ccccccccccc1', 'node_post', $1)",
            evidence_id,
        )
        await conn.execute(
            """
            insert into source_post_voice values
                ($1, 'voc', true, 'truth_observed', $2, $2, null, null),
                ($1, 'vops', false, 'truth_inferred', $2, $2, null,
                 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1'),
                ($1, 'voe', false, 'truth_proposed', $2, $2, null,
                 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2')
            """,
            post_id,
            recorded,
        )
        admitted = await _load_voice_assignments(
            conn, [post_id, evidence_id],
            knowledge_cutoff=None, snapshot_at=recorded + timedelta(days=1),
        )
        assert [row.voice_type_code for row in admitted] == ["voc", "vops"]
        assert admitted[1].evidence_post_id == evidence_id
        assert admitted[1].post_id == post_id
        assert admitted[1].truth_status_code == "truth_inferred"
        hidden = await _load_voice_assignments(
            conn, [post_id],
            knowledge_cutoff=None, snapshot_at=recorded + timedelta(days=1),
        )
        assert [row.voice_type_code for row in hidden] == ["voc"]
        earlier = await _load_voice_assignments(
            conn, [post_id, evidence_id],
            knowledge_cutoff=recorded - timedelta(seconds=1),
            snapshot_at=recorded + timedelta(days=1),
        )
        assert earlier == ()
    finally:
        await conn.close()
