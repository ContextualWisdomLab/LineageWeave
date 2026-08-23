"""Real-database tests for ADR 0144's account_observed_entity mechanism.

Applies every migration to a throwaway PostgreSQL database, same
convention as tests/test_synthetic_seed_cleanup.py and tests/test_schema.py.
Skipped unless a local PostgreSQL server is reachable.

Covers the ADR's three required tests exactly:
1. the write-time account set matches read_customer_master's own
   predicate (own-corp-or-public, gated by post eligibility);
2. narrowing a post's corporate_entity_id prunes its account_observed_entity
   links within the same synchronous reconciliation cycle;
3. entity_rows never surfaces a private post's counterparty (or its
   verified-but-never-mentioned ancestor) to a non-authorized account,
   across grant-then-narrow and narrow-then-grant orderings.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import asyncpg
import psycopg2
import pytest

from backend.app.auth import CurrentAccount
from backend.app.corporate_entity_ingestion import (
    prune_observed_entity_for_posts,
    record_observed_entity,
)
from backend.app.main import read_customer_master

_ADMIN_DSN = "postgresql://localhost/postgres"
_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _postgres_available() -> bool:
    try:
        conn = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        conn.close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


@pytest.fixture
def migrated_db():
    """A freshly migrated, throwaway database, dropped afterward."""
    db_name = f"lineageweave_observed_entity_test_{uuid.uuid4().hex[:12]}"
    admin_conn = psycopg2.connect(_ADMIN_DSN)
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(f'create database "{db_name}"')
    admin_conn.close()

    db_dsn = _ADMIN_DSN.rsplit("/", 1)[0] + f"/{db_name}"
    for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        subprocess.run(
            ["psql", "-X", "-v", "ON_ERROR_STOP=1", db_dsn, "-f", str(migration)],
            check=True,
        )

    yield db_dsn

    admin_conn = psycopg2.connect(_ADMIN_DSN)
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(
            "select pg_terminate_backend(pid) from pg_stat_activity where datname = %s",
            (db_name,),
        )
        cur.execute(f'drop database "{db_name}"')
    admin_conn.close()


async def _seed_corp(conn: asyncpg.Connection, code: str, name: str, parent_id: str | None = None) -> str:
    return await conn.fetchval(
        "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code, parent_entity_id) "
        "values ($1, $2, 'company', $3) returning corporate_entity_id",
        code,
        name,
        parent_id,
    )


async def _seed_account(conn: asyncpg.Connection, subject: str, name: str) -> str:
    return await conn.fetchval(
        "insert into user_account (external_subject_id, display_name, email_address) "
        "values ($1, $2, $3) returning user_account_id",
        subject,
        name,
        f"{subject}@example.test",
    )


async def _affiliate(conn: asyncpg.Connection, account_id: str, corp_id: str) -> None:
    await conn.execute(
        "insert into account_affiliation (user_account_id, corporate_entity_id) values ($1, $2)",
        account_id,
        corp_id,
    )


async def _seed_post(
    conn: asyncpg.Connection, author_id: str, corp_id: str, *, visibility: str = "internal"
) -> str:
    return await conn.fetchval(
        "insert into source_post "
        "(author_account_id, corporate_entity_id, post_title, post_body, voc_type_code, visibility_code, "
        " created_at, updated_at) "
        "values ($1, $2, 'Test post', 'Test body', 'voc', $3, now(), now()) "
        "returning post_id",
        author_id,
        corp_id,
        visibility,
    )


async def _seed_common_lookups(conn: asyncpg.Connection) -> None:
    # 'voc_type'/'voc' and 'corporate_entity_level'/'company' are already
    # seeded by migrations 0042 and 0016 respectively.
    await conn.execute(
        "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) values "
        "('post_visibility', 'public', 'Public'), "
        "('post_visibility', 'internal', 'Internal')"
    )


async def _account(pool: asyncpg.Pool, account_id: str) -> CurrentAccount:
    async with pool.acquire() as conn:
        corp_ids = await conn.fetch(
            "select corporate_entity_id from account_affiliation where user_account_id = $1",
            account_id,
        )
    return CurrentAccount(
        user_account_id=account_id,
        external_subject_id="test",
        display_name="Test",
        preferred_locale="en",
        corporate_entity_ids=frozenset(str(row["corporate_entity_id"]) for row in corp_ids),
        permission_codes=frozenset({"post_read"}),
    )


def test_write_time_account_set_matches_read_predicate(migrated_db: str) -> None:
    """Required test 1: the write-time set is exactly the read-time set."""

    async def run() -> None:
        conn = await asyncpg.connect(migrated_db)
        try:
            await _seed_common_lookups(conn)
            own_corp = await _seed_corp(conn, "OWN-01", "Our Company")
            other_corp = await _seed_corp(conn, "OTHER-01", "Unrelated Company")
            observed_corp = await _seed_corp(conn, "CUST-01", "Observed Counterparty")

            author = await _seed_account(conn, "author", "Author")
            await _affiliate(conn, author, own_corp)
            authorized_peer = await _seed_account(conn, "peer", "Authorized Peer")
            await _affiliate(conn, authorized_peer, own_corp)
            unrelated = await _seed_account(conn, "unrelated", "Unrelated Account")
            await _affiliate(conn, unrelated, other_corp)

            post = await _seed_post(conn, author, own_corp, visibility="internal")

            await record_observed_entity(conn, observed_corp, post)

            rows = await conn.fetch(
                "select account_id, granting_corporate_entity_id from account_observed_entity "
                "where corporate_entity_id = $1",
                observed_corp,
            )
            observed_accounts = {str(row["account_id"]) for row in rows}
            assert observed_accounts == {str(author), str(authorized_peer)}
            assert str(unrelated) not in observed_accounts
            for row in rows:
                assert str(row["granting_corporate_entity_id"]) == str(own_corp)
        finally:
            await conn.close()

    import asyncio

    asyncio.run(run())


def test_narrowing_prunes_within_one_synchronous_cycle(migrated_db: str) -> None:
    """Required test 2: reassignment away from an account's corp prunes it."""

    async def run() -> None:
        conn = await asyncpg.connect(migrated_db)
        try:
            await _seed_common_lookups(conn)
            own_corp = await _seed_corp(conn, "OWN-01", "Our Company")
            new_corp = await _seed_corp(conn, "NEW-01", "Reassigned-To Company")
            observed_corp = await _seed_corp(conn, "CUST-01", "Observed Counterparty")

            author = await _seed_account(conn, "author", "Author")
            await _affiliate(conn, author, own_corp)

            post = await _seed_post(conn, author, own_corp, visibility="internal")
            await record_observed_entity(conn, observed_corp, post)

            before = await conn.fetchval(
                "select count(*) from account_observed_entity where account_id = $1 and corporate_entity_id = $2",
                author,
                observed_corp,
            )
            assert before == 1

            # Narrow: reassign the post to a corp the author has no affiliation to.
            await conn.execute(
                "update source_post set corporate_entity_id = $1 where post_id = $2", new_corp, post
            )
            await prune_observed_entity_for_posts(conn, [post])

            after = await conn.fetchval(
                "select count(*) from account_observed_entity where account_id = $1 and corporate_entity_id = $2",
                author,
                observed_corp,
            )
            assert after == 0
        finally:
            await conn.close()

    import asyncio

    asyncio.run(run())


def test_entity_rows_never_leaks_across_grant_redaction_orderings(migrated_db: str) -> None:
    """Required test 3: a private post's counterparty ancestor never leaks.

    Revocation is live (no reconciliation lag, via the read-time join to
    account_affiliation); a new grant is not -- it needs the write-time
    hook to re-run (nightly backstop or fresh ingestion) before it takes
    effect. Both properties are asserted explicitly below.
    """

    async def run() -> None:
        pool = await asyncpg.create_pool(migrated_db, min_size=1, max_size=3)
        try:
            async with pool.acquire() as conn:
                await _seed_common_lookups(conn)
                own_corp = await _seed_corp(conn, "OWN-01", "Our Company")
                outsider_corp = await _seed_corp(conn, "OUT-01", "Outsider Company")
                ancestor_corp = await _seed_corp(conn, "ANCESTOR-01", "Group HQ (never mentioned)")
                leaf_corp = await _seed_corp(
                    conn, "LEAF-01", "Observed Subsidiary", parent_id=ancestor_corp
                )

                author = await _seed_account(conn, "author", "Author")
                await _affiliate(conn, author, own_corp)
                outsider = await _seed_account(conn, "outsider", "Outsider")
                await _affiliate(conn, outsider, outsider_corp)

                # Private (non-public) post owned by own_corp, observing leaf_corp
                # (whose real parent ancestor_corp is never itself mentioned).
                post = await _seed_post(conn, author, own_corp, visibility="internal")
                await record_observed_entity(conn, leaf_corp, post)

            # Ordering A: outsider is never granted own_corp -- must never see
            # either the leaf or its ancestor, regardless of the observation.
            leaf_id, ancestor_id = str(leaf_corp), str(ancestor_corp)

            outsider_account = await _account(pool, outsider)
            result = await read_customer_master(account=outsider_account, pool=pool)
            seen_ids = {row["corporate_entity_id"] for row in result["corporate_entities"]}
            assert leaf_id not in seen_ids
            assert ancestor_id not in seen_ids

            # Ordering B: grant outsider access to own_corp (widening). Per
            # the ADR, only revocation is live-via-the-join with no lag;
            # a new grant needs the write-time hook to re-run (nightly
            # reconciliation backstop, or a fresh ingestion event) before it
            # takes effect -- so granting alone must NOT leak early, and
            # replaying the hook must then correctly pick it up.
            async with pool.acquire() as conn:
                await _affiliate(conn, outsider, own_corp)
            outsider_account = await _account(pool, outsider)
            result = await read_customer_master(account=outsider_account, pool=pool)
            seen_ids = {row["corporate_entity_id"] for row in result["corporate_entities"]}
            assert leaf_id not in seen_ids
            assert ancestor_id not in seen_ids

            async with pool.acquire() as conn:
                await record_observed_entity(conn, leaf_corp, post)
            outsider_account = await _account(pool, outsider)
            result = await read_customer_master(account=outsider_account, pool=pool)
            seen_ids = {row["corporate_entity_id"] for row in result["corporate_entities"]}
            assert leaf_id in seen_ids
            assert ancestor_id in seen_ids
            ancestor_row = next(r for r in result["corporate_entities"] if r["corporate_entity_id"] == ancestor_id)
            assert "observed_hierarchy" in ancestor_row["scope_facets"]

            # Ordering C: redact (revoke) that same grant -- must immediately
            # stop seeing both again, with no separate reconciliation pass
            # needed (the read-time join to account_affiliation is live).
            async with pool.acquire() as conn:
                await conn.execute(
                    "delete from account_affiliation where user_account_id = $1 and corporate_entity_id = $2",
                    outsider,
                    own_corp,
                )
            outsider_account = await _account(pool, outsider)
            result = await read_customer_master(account=outsider_account, pool=pool)
            seen_ids = {row["corporate_entity_id"] for row in result["corporate_entities"]}
            assert leaf_id not in seen_ids
            assert ancestor_id not in seen_ids

            # The author, still affiliated with own_corp throughout, always
            # sees both.
            author_account = await _account(pool, author)
            result = await read_customer_master(account=author_account, pool=pool)
            seen_ids = {row["corporate_entity_id"] for row in result["corporate_entities"]}
            assert leaf_id in seen_ids
            assert ancestor_id in seen_ids
        finally:
            await pool.close()

    import asyncio

    asyncio.run(run())
