"""Real disposable PostgreSQL exercises for the five backend review findings."""
import asyncio
from contextlib import nullcontext

import asyncpg
import psycopg2
import pytest
from fastapi import HTTPException

from backend.app import customer_hint_ingestion as customer, main, post_chat_ingestion as chat
from backend.app.auth import CurrentAccount
from lineageweave.post_chat import ChatAnswer
from tests.test_customer_hint_resolution_postgresql import (
    customer_resolution_dsn,
    _seed_cross_tenant_hint,
    _ResolutionClient,
    _VerificationClient,
    _HierarchyClient,
    _corroborated_resolution,
)


def _account(seed, *, broad=False):
    return CurrentAccount(user_account_id="synthetic-reader", external_subject_id="synthetic-reader",
                          display_name="Synthetic reader", preferred_locale="en",
                          corporate_entity_ids=frozenset({seed["tenant_a_id"], seed["tenant_b_id"]} if broad else {seed["tenant_a_id"]}),
                          process_unit_ids=frozenset(), permission_codes=frozenset({"post_read"}))


def _mutate(dsn, sql, args):
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
    finally:
        conn.close()


@pytest.mark.parametrize("case", ["positive", "focal_abac", "linked_abac", "focal_draft", "linked_deleted"])
def test_postgresql_focal_and_linked_chat_capture_uses_canonical_eligibility(customer_resolution_dsn, case):
    """The real SQL and per-row ABAC reject only the affected focal/linked sources."""
    dsn = customer_resolution_dsn
    seed = _seed_cross_tenant_hint(dsn)
    _mutate(dsn, "update source_post set corporate_entity_id=%s, process_unit_id=%s where post_id=%s",
            (seed["tenant_a_id"], seed["tenant_a_pu"], seed["post_b"]))
    _mutate(dsn, "insert into post_lineage_edge (parent_post_id, child_post_id, fused_score, interval_relation_code) values (%s,%s,1,'interval_before')",
            (seed["post_a"], seed["post_b"]))
    if case.endswith("abac"):
        target = seed["post_a"] if case.startswith("focal") else seed["post_b"]
        _mutate(dsn, "update source_post set corporate_entity_id=%s where post_id=%s", (seed["tenant_b_id"], target))
    elif case == "focal_draft":
        _mutate(dsn, "update source_post set source_draft_code='DRAFT' where post_id=%s", (seed["post_a"],))
    elif case == "linked_deleted":
        _mutate(dsn, "update source_post set source_deleted_flag='DELETED' where post_id=%s", (seed["post_b"],))

    async def exercise():
        conn = await asyncpg.connect(dsn)
        try:
            return await chat.gather_chat_sources(conn, seed["post_a"], lambda row: main._can_see_post(_account(seed), row))
        finally:
            await conn.close()

    sources = asyncio.run(exercise())
    expected = [] if case.startswith("focal") else ([seed["post_a"], seed["post_b"]] if case == "positive" else [seed["post_a"]])
    assert [s.post_id for s in sources] == expected


@pytest.mark.parametrize("case", ["positive", "revoke_focal", "revoke_uncited", "delete_uncited", "draft_uncited"])
def test_postgresql_live_generation_final_source_reauthorization(customer_resolution_dsn, monkeypatch, case):
    """Execute actual endpoint, capture, final share locks, persistence and serialization."""
    dsn = customer_resolution_dsn
    seed = _seed_cross_tenant_hint(dsn)
    _mutate(dsn, "update source_post set corporate_entity_id=%s, process_unit_id=%s where post_id=%s",
            (seed["tenant_a_id"], seed["tenant_a_pu"], seed["post_b"]))
    _mutate(dsn, "insert into post_lineage_edge (parent_post_id, child_post_id, fused_score, interval_relation_code) values (%s,%s,1,'interval_before')",
            (seed["post_a"], seed["post_b"]))
    question = "Synthetic final authorization question"
    pool_holder = []

    class Client:
        available = True

        def answer(self, _question, sources):
            assert [s.post_id for s in sources] == [seed["post_a"], seed["post_b"]]
            assert pool_holder[0].get_idle_size() == pool_holder[0].get_size()
            if case.startswith("revoke"):
                target = seed["post_a"] if case == "revoke_focal" else seed["post_b"]
                _mutate(dsn, "update source_post set corporate_entity_id=%s where post_id=%s", (seed["tenant_b_id"], target))
            elif case == "draft_uncited":
                _mutate(dsn, "update source_post set source_draft_code='DRAFT' where post_id=%s", (seed["post_b"],))
            elif case == "delete_uncited":
                _mutate(dsn, "delete from post_lineage_edge where child_post_id=%s", (seed["post_b"],))
                _mutate(dsn, "delete from source_post where post_id=%s", (seed["post_b"],))
            return ChatAnswer("Synthetic source-grounded answer", (seed["post_a"],))

    async def activity(*_args):
        pass

    monkeypatch.setattr(main, "_post_chat_client", Client)
    monkeypatch.setattr(main, "_vision_client", lambda: None)
    monkeypatch.setattr(main, "use_llm_metadata", lambda *_args: nullcontext())
    monkeypatch.setattr(main, "traced", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(main, "publish_activity_event", activity)
    original_summaries = main.cited_post_summaries

    def serialized(sources, cited):
        # A conflicting source write on another real connection must block until
        # the final transaction (including serializer) has finished.
        blocker = psycopg2.connect(dsn)
        try:
            with blocker.cursor() as cursor:
                cursor.execute("set local lock_timeout='100ms'")
                with pytest.raises(psycopg2.errors.LockNotAvailable):
                    cursor.execute("update source_post set post_title='Synthetic concurrent title' where post_id=%s", (seed["post_b"],))
        finally:
            blocker.rollback()
            blocker.close()
        return original_summaries(sources, cited)

    monkeypatch.setattr(main, "cited_post_summaries", serialized)

    async def exercise():
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
        pool_holder.append(pool)
        try:
            call = main.chat_about_post(seed["post_a"], main.ChatRequest(question=question), _account(seed), pool, object())
            if case == "positive":
                result = await call
                assert result["answer_text"] == "Synthetic source-grounded answer"
                assert result["source_post_ids"] == [seed["post_a"], seed["post_b"]]
            else:
                with pytest.raises(HTTPException) as denied:
                    await call
                assert denied.value.status_code == 409
            async with pool.acquire() as conn:
                count = await conn.fetchval("select count(*) from post_chat_result where post_id=$1", seed["post_a"])
                assert count == (1 if case == "positive" else 0)
        finally:
            await pool.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("field", ["post_title", "post_body"])
def test_postgresql_customer_edit_during_generation_rejects_stale_digest(customer_resolution_dsn, monkeypatch, field):
    """Actual full-body digest catches edits after the bounded excerpt as well as title edits."""
    dsn = customer_resolution_dsn
    seed = _seed_cross_tenant_hint(dsn)
    original = "Synthetic customer evidence " + "x" * 21000
    _mutate(dsn, "update source_post set post_body=%s where post_id=%s", (original, seed["post_a"]))

    def corroborate(_hint, excerpt, *_clients):
        assert len(excerpt) < 2000
        if field == "post_title":
            _mutate(dsn, "update source_post set post_title='Synthetic edited title' where post_id=%s", (seed["post_a"],))
        else:
            _mutate(dsn, "update source_post set post_body=%s where post_id=%s", (original + "edited tail", seed["post_a"]))
        return _corroborated_resolution()

    monkeypatch.setattr(customer, "resolve_and_verify_organization_name", corroborate)

    async def exercise():
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
        try:
            result = await customer.resolve_customer_hint(pool, _ResolutionClient(), _VerificationClient(), _HierarchyClient(), seed["hint_code"], [seed["tenant_a_id"]], [])
            assert result is None
            async with pool.acquire() as conn:
                assert await conn.fetchval("select count(*) from source_post_customer_resolution") == 0
        finally:
            await pool.close()

    asyncio.run(exercise())


def test_postgresql_customer_single_source_derivation_and_read_edit_gate(customer_resolution_dsn, monkeypatch):
    """Narrow GET/deletion cannot reveal B-derived identity on unsupported A; edits hide stale B."""
    dsn = customer_resolution_dsn
    seed = _seed_cross_tenant_hint(dsn)
    seen = []

    def corroborate(_hint, excerpt, *_clients):
        seen.append(excerpt)
        return _corroborated_resolution() if "Synthetic b body" in excerpt else None

    monkeypatch.setattr(customer, "resolve_and_verify_organization_name", corroborate)

    async def exercise():
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
        try:
            result = await customer.resolve_customer_hint(pool, _ResolutionClient(), _VerificationClient(), _HierarchyClient(), seed["hint_code"], list(_account(seed, broad=True).corporate_entity_ids), [])
            assert result["linked_post_count"] == 1 and len(seen) == 2
            broad = await main.read_customer_master(_account(seed, broad=True), pool)
            assert broad["source_customer_hints"][0]["resolved_corporate_entity_id"] == seed["resolved_id"]
            narrow = await main.read_customer_master(_account(seed), pool)
            assert narrow["source_customer_hints"][0]["resolution_status"] == "hint_only"
            _mutate(dsn, "update source_post set post_body='Synthetic edited customer evidence' where post_id=%s", (seed["post_b"],))
            edited = await main.read_customer_master(_account(seed, broad=True), pool)
            assert edited["source_customer_hints"][0]["resolution_status"] == "hint_only"
            _mutate(dsn, "delete from source_post where post_id=%s", (seed["post_b"],))
            deleted = await main.read_customer_master(_account(seed), pool)
            assert deleted["source_customer_hints"][0]["resolution_status"] == "hint_only"
        finally:
            await pool.close()

    asyncio.run(exercise())


@pytest.mark.parametrize("narrow", [False, True])
def test_postgresql_replay_narrower_process_reader_denies_derived_text(customer_resolution_dsn, narrow):
    """Current real repository/endpoint boundary checks normalized process generation scope."""
    from dataclasses import replace
    from backend.app.post_chat_replay_policy import PostChatAuthorizationScope

    dsn = customer_resolution_dsn
    seed = _seed_cross_tenant_hint(dsn)
    reader = replace(_account(seed), process_unit_ids=frozenset({seed["tenant_a_pu"]}) if narrow else frozenset())
    answer = "Synthetic unrestricted-process answer"

    async def exercise():
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                await chat.persist_post_chat(conn, seed["post_a"], "Synthetic replay question", answer,
                                             [seed["post_a"]],
                                             PostChatAuthorizationScope.captured(corporate_entity_ids={seed["tenant_a_id"]}, process_unit_ids=set()),
                                             [seed["post_a"]])
            history = await main.read_post_chat(seed["post_a"], reader, pool)
            assert bool(history["exchanges"]) is (not narrow)
            async with pool.acquire() as conn:
                stored = await chat.fetch_persisted_chat(conn, seed["post_a"], "Synthetic replay question",
                                                       PostChatAuthorizationScope.captured(corporate_entity_ids=reader.corporate_entity_ids,
                                                                                          process_unit_ids=reader.process_unit_ids))
            if narrow:
                assert stored is None
            else:
                assert stored["answer_text"] == answer
        finally:
            await pool.close()

    asyncio.run(exercise())
