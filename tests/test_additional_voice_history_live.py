"""Synthetic PostgreSQL proof of additional-Voice correction history (ADR 0256)."""

from __future__ import annotations

import asyncio
import os
from contextlib import closing

import asyncpg
import pytest

from backend.app.source_post_voice_ingestion import (
    PrimaryVoiceAssignmentError,
    persist_additional_voice_assignment,
)
from test_source_post_voice_history_live import (
    _connect,
    _insert_synthetic_post,
    _postgres_available,
    voice_history_dsn,  # noqa: F401 -- reuse the full-schema database fixture
)

pytestmark = pytest.mark.skipif(
    not _postgres_available(), reason="synthetic PostgreSQL test database unavailable"
)

_HISTORY = """
select voice.voice_assignment_id, voice.truth_status_code,
       voice.effective_from, voice.effective_to, voice.recorded_at,
       voice.provenance_assertion_id, assertion.subject_resource_id,
       evidence.node_id as evidence_post_id
  from source_post_voice voice
  join provenance_assertion assertion
    on assertion.assertion_id = voice.provenance_assertion_id
  join provenance_resource_binding evidence
    on evidence.resource_id = assertion.object_resource_id
 where voice.post_id = $1::uuid and voice.voice_type_code = 'vops'
 order by voice.effective_from
"""


def _posts(dsn: str) -> tuple[str, str, str]:
    with closing(_connect(dsn)) as connection, connection.cursor() as cursor:
        cursor.execute(
            "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) "
            "values ('node_type', 'node_post', 'Post') on conflict do nothing"
        )
        return tuple(_insert_synthetic_post(cursor) for _ in range(3))


async def _write(conn, post, evidence, truth="truth_observed"):
    await persist_additional_voice_assignment(
        conn, post_id=post, voice_type_code="vops",
        truth_status_code=truth, evidence_post_id=evidence,
    )


def test_correction_preserves_cutoff_and_distinct_provenance(voice_history_dsn):
    """Changing evidence retains the first interval; an exact retry changes nothing."""
    post, first_evidence, second_evidence = _posts(voice_history_dsn)

    async def exercise():
        conn = await asyncpg.connect(voice_history_dsn)
        try:
            await _write(conn, post, first_evidence)
            before = dict((await conn.fetch(_HISTORY, post))[0])
            cutoff = await conn.fetchval("select clock_timestamp()")
            await _write(conn, post, second_evidence, "truth_proposed")
            rows = await conn.fetch(_HISTORY, post)
            assert len(rows) == 2
            historical, current = map(dict, rows)
            assert historical | {"effective_to": None} == before
            assert historical["effective_to"] == current["effective_from"]
            assert historical["effective_from"] <= cutoff < historical["effective_to"]
            assert str(historical["evidence_post_id"]) == first_evidence
            assert str(current["evidence_post_id"]) == second_evidence
            assert current["truth_status_code"] == "truth_proposed"
            assert current["effective_to"] is None
            assert current["subject_resource_id"] != historical["subject_resource_id"]
            assert current["provenance_assertion_id"] != historical["provenance_assertion_id"]
            await _write(conn, post, second_evidence, "truth_proposed")
            assert [dict(row) for row in await conn.fetch(_HISTORY, post)] == [historical, current]
            await _write(conn, post, first_evidence)
            assert len(await conn.fetch(_HISTORY, post)) == 3
        finally:
            await conn.close()

    asyncio.run(exercise())


@pytest.mark.skipif(
    os.environ.get("LINEAGEWEAVE_TEST_VOICE_OIDC") != "1",
    reason="opt in with the synthetic Compose OIDC and Valkey services",
)
def test_authenticated_api_retains_prior_truth_and_rejects_hidden_evidence(
    voice_history_dsn, monkeypatch,
):
    """Real JWKS, RBAC, PostgreSQL, and Valkey preserve the authorized API history."""
    import httpx
    import redis.asyncio as redis

    from backend.app import main
    from backend.app.activity_stream import _stream_key, get_valkey
    from backend.app.auth import _decode_access_token
    from backend.app.config import load_settings
    from backend.app.db import get_pool
    from lineageweave.http_client import post_form

    for key in os.environ:
        if key.startswith(("KEYVERSE_", "OIDC_", "KEYCLOAK_")):
            monkeypatch.delenv(key)
    token = post_form(
        "http://localhost:18080/realms/lineageweave-demo/protocol/openid-connect/token",
        {"client_id": "lineageweave-frontend", "grant_type": "password",
         "username": "demo.analyst", "password": "lineageweave-demo-only"},
        timeout=10,
    )["access_token"]
    subject = _decode_access_token(token, load_settings())["sub"]
    post, evidence, hidden = _posts(voice_history_dsn)

    async def exercise():
        pool = await asyncpg.create_pool(voice_history_dsn, min_size=1, max_size=2)
        valkey = redis.from_url("redis://localhost:16379/0", decode_responses=True)
        overrides = main.app.dependency_overrides.copy()
        main.app.dependency_overrides[get_pool] = lambda: pool
        main.app.dependency_overrides[get_valkey] = lambda: valkey
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) values "
                    "('post_visibility','public','Public'), ('permission','post_read','Read posts'), "
                    "('permission','post_admin','Manage posts') on conflict do nothing"
                )
                await conn.execute("update source_post set visibility_code='public' where post_id=any($1::uuid[])", [post, evidence])
                account = await conn.fetchval(
                    "insert into user_account (external_subject_id,display_name,email_address) "
                    "values ($1,'Synthetic API reviewer','voice-api@example.test') returning user_account_id", subject,
                )
                role = await conn.fetchval(
                    "insert into access_role (role_code,role_name) values ('voice_history_test','Synthetic Voice reviewer') returning access_role_id"
                )
                await conn.execute("insert into account_role_assignment values ($1,$2)", account, role)
                await conn.execute("insert into role_permission values ($1,'post_read')", role)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://synthetic.test") as client:
                route = f"/api/posts/{post}/voice-assignments"
                payload = {"voice_type_code": "vops", "truth_status_code": "truth_observed", "evidence_post_id": evidence}
                assert (await client.post(route, json=payload)).status_code == 401
                client.headers["Authorization"] = f"Bearer {token}"
                assert (await client.post(route, json=payload)).status_code == 403
                async with pool.acquire() as conn:
                    await conn.execute("insert into role_permission values ($1,'post_admin')", role)
                assert (await client.post(route, json=payload | {"evidence_post_id": hidden})).status_code == 403
                assert (await client.post(route, json=payload)).status_code == 201
                async with pool.acquire() as conn:
                    cutoff = await conn.fetchval("select clock_timestamp()")
                assert (await client.post(route, json=payload | {"truth_status_code": "truth_proposed"})).status_code == 201
                historical = await client.get(f"/api/posts/{post}", params={"as_of": cutoff.isoformat()})
                live = await client.get(f"/api/posts/{post}")
                assert historical.status_code == live.status_code == 200
                prior_voices, current_voices = historical.json()["voice_types"], live.json()["voice_types"]
                assert next(v for v in prior_voices if v["code"] == "vops")["truth_status_code"] == "truth_observed"
                assert next(v for v in current_voices if v["code"] == "vops")["truth_status_code"] == "truth_proposed"
                assert next(v for v in current_voices if v["is_primary"])["code"] == "voc"
                assert hidden not in historical.text + live.text
                async with pool.acquire() as conn:
                    assert len(await conn.fetch(_HISTORY, post)) == 2
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(overrides)
            await valkey.delete(_stream_key(post))
            await valkey.aclose()
            await pool.close()

    asyncio.run(exercise())


def test_invalid_correction_and_primary_conflict_leave_no_partial_write(voice_history_dsn):
    """A rejected correction keeps the old evidence and rolls back new provenance."""
    post, evidence, replacement = _posts(voice_history_dsn)

    async def exercise():
        conn = await asyncpg.connect(voice_history_dsn)
        try:
            await _write(conn, post, evidence)
            before = await conn.fetch(_HISTORY, post)
            count = await conn.fetchval("select count(*) from provenance_resource")
            with pytest.raises((asyncpg.CheckViolationError, asyncpg.ForeignKeyViolationError)):
                await _write(conn, post, replacement, "invalid_synthetic_truth")
            assert await conn.fetch(_HISTORY, post) == before
            assert await conn.fetchval("select count(*) from provenance_resource") == count
            with pytest.raises(PrimaryVoiceAssignmentError):
                await persist_additional_voice_assignment(
                    conn, post_id=post, voice_type_code="voc",
                    truth_status_code="truth_observed", evidence_post_id=replacement,
                )
            assert await conn.fetchval("select count(*) from provenance_resource") == count
        finally:
            await conn.close()

    asyncio.run(exercise())


def test_waiting_correction_uses_post_lock_clock_and_preserves_primary(voice_history_dsn):
    """A write begun before its predecessor cannot backdate the next interval."""
    post, first_evidence, second_evidence = _posts(voice_history_dsn)

    async def exercise():
        first = await asyncpg.connect(voice_history_dsn)
        second = await asyncpg.connect(voice_history_dsn)
        task = None
        try:
            await _write(first, post, first_evidence)
            async with first.transaction():
                await first.execute("select post_id from source_post where post_id=$1::uuid for update", post)
                task = asyncio.create_task(_write(second, post, first_evidence))
                # Observe actual PostgreSQL lock waiting, not a guessed sleep interval.
                async with asyncio.timeout(5):
                    while not await first.fetchval(
                        "select exists(select 1 from pg_stat_activity where pid=$1 and wait_event_type='Lock')",
                        second.get_server_pid(),
                    ):
                        await asyncio.sleep(0)
                await _write(first, post, second_evidence)
            await asyncio.wait_for(task, 5)
            rows = await first.fetch(_HISTORY, post)
            assert len(rows) == 3
            assert rows[0]["effective_to"] == rows[1]["effective_from"]
            assert rows[1]["effective_to"] == rows[2]["effective_from"]
            assert rows[0]["effective_from"] < rows[1]["effective_from"] < rows[2]["effective_from"]
            assert rows[2]["effective_to"] is None
            assert await first.fetchval(
                "select voice_type_code from source_post_voice where post_id=$1::uuid and is_primary and effective_to is null", post,
            ) == "voc"
        finally:
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await first.close()
            await second.close()

    asyncio.run(exercise())
