"""Real OIDC/PostgreSQL proof that Voice reads reauthorize their evidence."""

from __future__ import annotations

import asyncio
import os
from contextlib import closing

import asyncpg
import httpx
import pytest
import redis.asyncio as redis

from backend.app import main
from backend.app.activity_stream import _stream_key, get_valkey
from backend.app.auth import CurrentAccount, _decode_access_token
from backend.app.config import load_settings
from backend.app.db import get_pool
from lineageweave.http_client import post_form
from test_source_post_voice_history_live import (
    _connect,
    _insert_synthetic_post,
    _postgres_available,
    voice_history_dsn,  # noqa: F401 -- full migration fixture, synthetic database only
)


pytestmark = pytest.mark.skipif(
    not _postgres_available()
    or os.environ.get("LINEAGEWEAVE_TEST_VOICE_OIDC") != "1",
    reason="requires synthetic PostgreSQL and opt-in Compose OIDC/Valkey",
)


def test_voice_reads_reauthorize_evidence_without_changing_assignments(
    voice_history_dsn, monkeypatch,
):
    """Hidden/draft/deleted evidence disappears from detail, list and filters."""
    for key in list(os.environ):
        if key.startswith(("KEYVERSE_", "OIDC_", "KEYCLOAK_")):
            monkeypatch.delenv(key)
    token = post_form(
        "http://localhost:18080/realms/lineageweave-demo/protocol/openid-connect/token",
        {"client_id": "lineageweave-frontend", "grant_type": "password",
         "username": "demo.analyst", "password": "lineageweave-demo-only"},
        timeout=10,
    )["access_token"]
    subject = _decode_access_token(token, load_settings())["sub"]
    with closing(_connect(voice_history_dsn)) as conn, conn.cursor() as cursor:
        cursor.execute(
            "insert into common_lookup_value (lookup_category,lookup_code,lookup_label) "
            "values ('node_type','node_post','Post') on conflict do nothing"
        )
        post, evidence = [_insert_synthetic_post(cursor) for _ in range(2)]

    async def exercise():
        pool = await asyncpg.create_pool(voice_history_dsn, min_size=1, max_size=2)
        valkey = redis.from_url("redis://localhost:16379/0", decode_responses=True)
        overrides = main.app.dependency_overrides.copy()
        main.app.dependency_overrides[get_pool] = lambda: pool
        main.app.dependency_overrides[get_valkey] = lambda: valkey
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "insert into common_lookup_value (lookup_category,lookup_code,lookup_label) values "
                    "('post_visibility','public','Public'), ('post_visibility','private','Private'), "
                    "('permission','post_read','Read posts'), ('permission','post_admin','Manage posts') "
                    "on conflict do nothing"
                )
                await conn.execute(
                    "update source_post set visibility_code='public' where post_id=any($1::uuid[])",
                    [post, evidence],
                )
                account = await conn.fetchval(
                    "insert into user_account (external_subject_id,display_name,email_address) "
                    "values ($1,'Synthetic visibility reviewer','visibility@example.test') returning user_account_id",
                    subject,
                )
                role = await conn.fetchval(
                    "insert into access_role (role_code,role_name) "
                    "values ('voice_visibility_test','Synthetic reviewer') returning access_role_id"
                )
                await conn.execute("insert into account_role_assignment values ($1,$2)", account, role)
                await conn.execute(
                    "insert into role_permission values ($1,'post_read'),($1,'post_admin')", role,
                )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=main.app), base_url="http://synthetic.test",
            ) as client:
                assert (await client.get(f"/api/posts/{post}")).status_code == 401
                client.headers["Authorization"] = f"Bearer {token}"
                created = await client.post(
                    f"/api/posts/{post}/voice-assignments",
                    json={"voice_type_code": "vops", "truth_status_code": "truth_proposed",
                          "evidence_post_id": evidence},
                )
                assert created.status_code == 201
                async with pool.acquire() as conn:
                    cutoff = await conn.fetchval("select clock_timestamp()")
                    stored = await conn.fetch(
                        "select * from source_post_voice where post_id=$1::uuid order by voice_type_code", post,
                    )

                async def assert_views(visible):
                    for params in ({}, {"as_of": cutoff.isoformat()}):
                        detail = await client.get(f"/api/posts/{post}", params=params)
                        assert detail.status_code == 200
                        voices = detail.json()["voice_types"]
                        assert {v["code"] for v in voices} == ({"voc", "vops"} if visible else {"voc"})
                        if visible:
                            assert next(v for v in voices if v["code"] == "vops")["truth_status_code"] == "truth_proposed"
                        assert evidence not in detail.text
                    listed = await client.get("/api/posts")
                    assert listed.status_code == 200
                    body = listed.json()
                    carrying = next(p for p in body["posts"] if p["post_id"] == post)
                    assert {v["code"] for v in carrying["voice_types"]} == ({"voc", "vops"} if visible else {"voc"})
                    assert ("vops" in {v["code"] for v in body["voc_type_options"]}) is visible
                    filtered = await client.get("/api/posts", params={"voc_type": "vops"})
                    assert filtered.status_code == 200
                    assert filtered.json()["total_count"] == (1 if visible else 0)
                    assert {p["post_id"] for p in filtered.json()["posts"]} == ({post} if visible else set())

                await assert_views(True)
                async with pool.acquire() as conn:
                    entity = await conn.fetchval(
                        "select corporate_entity_id from source_post where post_id=$1::uuid", evidence,
                    )
                    process = await conn.fetchval(
                        "insert into process_unit (corporate_entity_id,process_unit_code,process_unit_name) "
                        "values ($1,'synthetic-visible-process','Synthetic process') returning process_unit_id", entity,
                    )
                    await conn.execute(
                        "insert into account_affiliation (user_account_id,corporate_entity_id,process_unit_id) "
                        "values ($1,$2,$3)", account, entity, process,
                    )
                    await conn.execute(
                        "update source_post set visibility_code='private',process_unit_id=null "
                        "where post_id=$1::uuid", evidence,
                    )
                    scoped_account = CurrentAccount(
                        str(account), subject, "Synthetic reviewer", None,
                        frozenset({str(entity)}), frozenset({str(process)}),
                        frozenset({"post_read"}),
                    )
                    scoped = await main._load_post_voice_types(conn, post, scoped_account)
                    assert {v["code"] for v in scoped} == {"voc"}
                    options, _ = await main._post_filter_options(
                        conn, scoped_account.corporate_entity_ids, scoped_account.process_unit_ids,
                    )
                    assert "vops" not in {v["code"] for v in options}
                # The local demo issuer grants corporation-wide scope. Exact
                # process-unit scope above uses the same production read boundary.
                await assert_views(True)
                async with pool.acquire() as conn:
                    await conn.execute(
                        "update source_post set process_unit_id=$2 where post_id=$1::uuid", evidence, process,
                    )
                    scoped = await main._load_post_voice_types(conn, post, scoped_account)
                    assert {v["code"] for v in scoped} == {"voc", "vops"}
                await assert_views(True)
                async with pool.acquire() as conn:
                    await conn.execute(
                        "delete from account_affiliation where user_account_id=$1", account,
                    )
                for visibility, draft, deleted in [
                    ("private", None, None), ("public", "X", None), ("public", None, "X"),
                ]:
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "update source_post set visibility_code=$2,source_draft_code=$3,source_deleted_flag=$4 "
                            "where post_id=$1::uuid", evidence, visibility, draft, deleted,
                        )
                    await assert_views(False)
                async with pool.acquire() as conn:
                    await conn.execute(
                        "update source_post set source_deleted_flag=null where post_id=$1::uuid", evidence,
                    )
                    assert await conn.fetch(
                        "select * from source_post_voice where post_id=$1::uuid order by voice_type_code", post,
                    ) == stored
                await assert_views(True)
                persist = main.persist_additional_voice_assignment

                async def persist_then_withdraw(conn, **kwargs):
                    await persist(conn, **kwargs)
                    await conn.execute(
                        "update source_post set visibility_code='private' where post_id=$1::uuid", evidence,
                    )

                monkeypatch.setattr(main, "persist_additional_voice_assignment", persist_then_withdraw)
                revoked_write = await client.post(
                    f"/api/posts/{post}/voice-assignments",
                    json={"voice_type_code": "voe", "truth_status_code": "truth_proposed",
                          "evidence_post_id": evidence},
                )
                assert revoked_write.status_code == 409
                assert evidence not in revoked_write.text
                assert "Reopen the post" in revoked_write.json()["detail"]
                async with pool.acquire() as conn:
                    assert not await conn.fetchval(
                        "select exists (select 1 from source_post_voice "
                        "where post_id=$1::uuid and voice_type_code='voe')", post,
                    )
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(overrides)
            await valkey.delete(_stream_key(post))
            await valkey.aclose()
            await pool.close()

    asyncio.run(exercise())
