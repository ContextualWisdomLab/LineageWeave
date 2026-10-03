"""Live PostgreSQL proof of ADR 0252 primary Voice history.

Skipped unless a local PostgreSQL server is reachable
(LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN), matching tests/test_schema.py.
Synthetic fixtures only: no real organization, person, or record ids.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import threading
import uuid
from datetime import datetime, timedelta
from itertools import pairwise
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import psycopg2.errors
import pytest

from backend.app.source_post_voice_ingestion import persist_additional_voice_assignment

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS_DIR = _ROOT / "migrations"
_HISTORY_MIGRATION = _MIGRATIONS_DIR / "0243_source_post_voice_history.sql"
_COMBINATION_MIGRATION = _MIGRATIONS_DIR / "0237_source_post_voice_combination.sql"

# Production post-detail cutoff predicate (ADR 0252 / backend.app.main).
_API_CUTOFF_SQL = """
select voice.voice_type_code
  from source_post_voice voice
 where voice.post_id = %s
   and voice.is_primary
   and ((%s::timestamptz is null and voice.effective_to is null)
        or (%s::timestamptz is not null
            and voice.effective_from <= %s
            and (voice.effective_to is null or %s < voice.effective_to)))
"""

# Ontology continuation uses frozen snapshot_at when no cutoff is requested.
_ONTOLOGY_CUTOFF_SQL = """
select voice.voice_type_code
  from source_post_voice voice
 where voice.post_id = %s
   and voice.is_primary
   and voice.effective_from <= coalesce(%s::timestamptz, %s::timestamptz)
   and (
       voice.effective_to is null
       or coalesce(%s::timestamptz, %s::timestamptz) < voice.effective_to
   )
   and voice.recorded_at <= %s::timestamptz
"""


def _postgres_available() -> bool:
    try:
        conn = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        conn.close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)


def _database_dsn(database_name: str) -> str:
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def _apply_migrations(database_dsn: str) -> None:
    """Replay every numbered migration through psql, matching migrate.sh."""
    for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        subprocess.run(
            ["psql", "-X", "-v", "ON_ERROR_STOP=1", database_dsn, "-f", str(migration)],
            check=True,
            capture_output=True,
            text=True,
        )


@pytest.fixture(scope="module")
def voice_history_dsn():
    """Throwaway database with the full product schema, dropped afterward."""
    database_name = f"lineageweave_voice_hist_{uuid.uuid4().hex[:12]}"
    admin_conn = psycopg2.connect(_ADMIN_DSN)
    admin_conn.autocommit = True
    with admin_conn.cursor() as cursor:
        cursor.execute(f'create database "{database_name}"')
    admin_conn.close()
    database_dsn = _database_dsn(database_name)
    try:
        _apply_migrations(database_dsn)
        with _connect(database_dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                insert into common_lookup_value (lookup_category, lookup_code, lookup_label)
                values ('knowledge_graph_node_type', 'node_post', 'Post')
                on conflict (lookup_code) do nothing
                """
            )
        yield database_dsn
    finally:
        admin_conn = psycopg2.connect(_ADMIN_DSN)
        admin_conn.autocommit = True
        with admin_conn.cursor() as cursor:
            cursor.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where datname = %s and pid <> pg_backend_pid()",
                (database_name,),
            )
            cursor.execute(f'drop database "{database_name}"')
        admin_conn.close()


def _connect(database_dsn: str):
    connection = psycopg2.connect(database_dsn)
    connection.autocommit = True
    return connection


def _insert_synthetic_post(cursor, voc_type_code: str = "voc") -> str:
    """Insert one synthetic Post and return its UUID."""
    suffix = uuid.uuid4().hex[:12]
    cursor.execute(
        """
        insert into common_lookup_value
            (lookup_category, lookup_code, lookup_label)
        values ('post_visibility', %s, 'Synthetic public')
        on conflict (lookup_code) do nothing
        """,
        (f"vis_{suffix}",),
    )
    visibility_code = f"vis_{suffix}"
    cursor.execute(
        """
        insert into user_account
            (external_subject_id, display_name, email_address)
        values (%s, 'Synthetic Voice Analyst', %s)
        returning user_account_id
        """,
        (f"synthetic-voice-{suffix}", f"synthetic-voice-{suffix}@example.test"),
    )
    account_id = cursor.fetchone()[0]
    cursor.execute(
        """
        insert into corporate_entity
            (corporate_entity_code, entity_name, entity_level_code)
        values (%s, 'Synthetic Voice Corp', 'company')
        returning corporate_entity_id
        """,
        (f"SYNTH-VOICE-{suffix}",),
    )
    entity_id = cursor.fetchone()[0]
    cursor.execute(
        """
        insert into source_post
            (author_account_id, corporate_entity_id, post_title, post_body,
             voc_type_code, visibility_code)
        values (%s, %s, 'Synthetic Voice history post', 'synthetic body', %s, %s)
        returning post_id
        """,
        (account_id, entity_id, voc_type_code, visibility_code),
    )
    return str(cursor.fetchone()[0])


def _primary_rows(cursor, post_id: str) -> list[tuple]:
    cursor.execute(
        """
        select voice_type_code, is_primary, effective_from, effective_to
          from source_post_voice
         where post_id = %s
           and is_primary
         order by effective_from, voice_type_code
        """,
        (post_id,),
    )
    return cursor.fetchall()


def test_additional_voice_reassertion_preserves_cutoff_evidence(
    voice_history_dsn,
) -> None:
    """Later truth/evidence writes cannot rewrite an earlier additional Voice."""
    import asyncpg

    from backend.app.main import _load_post_voice_types
    from backend.app.ontology_neighborhood_ingestion import _load_voice_assignments

    with _connect(voice_history_dsn) as connection, connection.cursor() as cursor:
        post_id = _insert_synthetic_post(cursor)
        first_evidence = _insert_synthetic_post(cursor)
        later_evidence = _insert_synthetic_post(cursor)

    async def exercise():
        conn = await asyncpg.connect(voice_history_dsn)
        try:

            async def assign(truth, evidence):
                await persist_additional_voice_assignment(
                    conn,
                    post_id=post_id,
                    voice_type_code="vops",
                    truth_status_code=truth,
                    evidence_post_id=evidence,
                )

            await assign("truth_proposed", first_evidence)
            first = await conn.fetchrow(
                "select * from source_post_voice where post_id = $1::uuid and not is_primary",
                post_id,
            )
            cutoff = await conn.fetchval("select clock_timestamp()")
            await assign("truth_proposed", first_evidence)
            assert (
                await conn.fetchrow(
                    "select * from source_post_voice where voice_assignment_id = $1",
                    first["voice_assignment_id"],
                )
                == first
            )
            await assign("truth_observed", first_evidence)
            await assign("truth_observed", later_evidence)
            rows = await conn.fetch(
                """
                select voice.*, binding.node_id as evidence_post_id
                  from source_post_voice voice
                  join provenance_assertion assertion
                    on assertion.assertion_id = voice.provenance_assertion_id
                  join provenance_resource_binding binding
                    on binding.resource_id = assertion.object_resource_id
                 where voice.post_id = $1::uuid and not voice.is_primary
                 order by voice.effective_from
                """,
                post_id,
            )
            assert len(rows) == 3
            old, intermediate, new = rows
            assert old["voice_assignment_id"] != new["voice_assignment_id"]
            assert old["truth_status_code"] == "truth_proposed"
            assert str(old["evidence_post_id"]) == first_evidence
            assert old["recorded_at"] == first["recorded_at"]
            assert old["effective_from"] == first["effective_from"]
            assert old["effective_to"] == intermediate["effective_from"]
            assert intermediate["truth_status_code"] == "truth_observed"
            assert str(intermediate["evidence_post_id"]) == first_evidence
            assert (
                intermediate["effective_to"]
                == new["effective_from"]
                == new["recorded_at"]
            )
            assert new["truth_status_code"] == "truth_observed"
            assert str(new["evidence_post_id"]) == later_evidence
            assert new["effective_to"] is None
            before_failure = await conn.fetchrow(
                "select * from source_post_voice where voice_assignment_id = $1",
                new["voice_assignment_id"],
            )
            with pytest.raises(asyncpg.CheckViolationError):
                await assign("truth_unsupported", first_evidence)
            assert (
                await conn.fetchrow(
                    "select * from source_post_voice where voice_assignment_id = $1",
                    new["voice_assignment_id"],
                )
                == before_failure
            )
            assert (
                await conn.fetchval(
                    "select count(*) from source_post_voice where post_id=$1::uuid and not is_primary",
                    post_id,
                )
                == 3
            )
            historical = await conn.fetchrow(
                """
                select voice_assignment_id, truth_status_code, provenance_assertion_id
                  from source_post_voice
                 where post_id = $1::uuid and not is_primary
                   and effective_from <= $2 and recorded_at <= $2
                   and (effective_to is null or $2 < effective_to)
                """,
                post_id,
                cutoff,
            )
            assert historical["voice_assignment_id"] == first["voice_assignment_id"]
            assert historical["truth_status_code"] == first["truth_status_code"]
            assert (
                historical["provenance_assertion_id"]
                == first["provenance_assertion_id"]
            )
            assert (
                await conn.fetchval(
                    "select voice_type_code from source_post_voice where post_id=$1::uuid and is_primary and effective_to is null",
                    post_id,
                )
                == "voc"
            )
            detail = await _load_post_voice_types(conn, post_id, cutoff)
            assert [
                (voice["code"], voice["truth_status_code"]) for voice in detail
            ] == [
                ("voc", "truth_observed"),
                ("vops", "truth_proposed"),
            ]
            snapshot_at = await conn.fetchval("select clock_timestamp()")
            assignments = await _load_voice_assignments(
                conn,
                [post_id, first_evidence, later_evidence],
                can_see_post=lambda _post: True,
                knowledge_cutoff=cutoff,
                snapshot_at=snapshot_at,
            )
            earlier = next(voice for voice in assignments if not voice.is_primary)
            assert earlier.evidence_post_id == first_evidence
            assert earlier.truth_status_code == "truth_proposed"
            # Emulate a legacy overwritten row whose original truth is lost.
            await conn.execute(
                "update source_post_voice set recorded_at=clock_timestamp() where voice_assignment_id=$1",
                first["voice_assignment_id"],
            )
            assert [
                voice["code"]
                for voice in await _load_post_voice_types(conn, post_id, cutoff)
            ] == ["voc"]
            assignments = await _load_voice_assignments(
                conn,
                [post_id, first_evidence, later_evidence],
                can_see_post=lambda _post: True,
                knowledge_cutoff=cutoff,
                snapshot_at=await conn.fetchval("select clock_timestamp()"),
            )
            assert all(voice.is_primary for voice in assignments)
        finally:
            await conn.close()

    asyncio.run(exercise())


def test_waiting_additional_voice_writer_uses_post_lock_clock(
    voice_history_dsn,
) -> None:
    """An earlier-started transaction cannot backdate a replacement after waiting."""
    import asyncpg

    with _connect(voice_history_dsn) as connection, connection.cursor() as cursor:
        post_id = _insert_synthetic_post(cursor)
        evidence = _insert_synthetic_post(cursor)

    async def exercise():
        first = await asyncpg.connect(voice_history_dsn)
        second = await asyncpg.connect(voice_history_dsn)
        observer = await asyncpg.connect(voice_history_dsn)
        pending = None
        try:

            async def assign(conn, truth):
                await persist_additional_voice_assignment(
                    conn,
                    post_id=post_id,
                    voice_type_code="vops",
                    truth_status_code=truth,
                    evidence_post_id=evidence,
                )

            await assign(first, "truth_proposed")
            second_pid = await second.fetchval("select pg_backend_pid()")
            async with first.transaction():
                await first.fetchval(
                    "select post_id from source_post where post_id=$1::uuid for update",
                    post_id,
                )
                pending = asyncio.create_task(assign(second, "truth_authoritative"))
                async with asyncio.timeout(5):
                    while not await observer.fetchval(
                        "select wait_event_type = 'Lock' from pg_stat_activity where pid=$1",
                        second_pid,
                    ):
                        await asyncio.sleep(0.001)
                await assign(first, "truth_observed")
            await asyncio.wait_for(pending, 5)
            rows = await first.fetch(
                """
                select truth_status_code, effective_from, effective_to, recorded_at
                  from source_post_voice where post_id=$1::uuid and not is_primary
                 order by effective_from
                """,
                post_id,
            )
            assert [row["truth_status_code"] for row in rows] == [
                "truth_proposed",
                "truth_observed",
                "truth_authoritative",
            ]
            for old, new in pairwise(rows):
                assert (
                    old["effective_from"] < old["effective_to"] == new["effective_from"]
                )
                assert new["recorded_at"] == new["effective_from"]
            assert rows[-1]["effective_to"] is None
        finally:
            if pending is not None and not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            await first.close()
            await second.close()
            await observer.close()

    asyncio.run(exercise())


def _api_primary(cursor, post_id: str, cutoff: datetime | None) -> list[str]:
    cursor.execute(
        _API_CUTOFF_SQL,
        (post_id, cutoff, cutoff, cutoff, cutoff),
    )
    return [row[0] for row in cursor.fetchall()]


def _ontology_primary(
    cursor,
    post_id: str,
    knowledge_cutoff: datetime | None,
    snapshot_at: datetime,
) -> list[str]:
    cursor.execute(
        _ONTOLOGY_CUTOFF_SQL,
        (
            post_id,
            knowledge_cutoff,
            snapshot_at,
            knowledge_cutoff,
            snapshot_at,
            snapshot_at,
        ),
    )
    return [row[0] for row in cursor.fetchall()]


def _insert_additional_voice(cursor, post_id: str, voice_type_code: str) -> None:
    """Attach one evidence-bearing additional Voice without touching the primary."""
    suffix = uuid.uuid4().hex
    cursor.execute(
        """
        insert into provenance_resource (resource_iri, resource_label)
        values (%s, 'Synthetic Voice assignment'), (%s, 'Synthetic Voice evidence')
        returning resource_id
        """,
        (
            f"urn:synthetic:voice-assignment:{suffix}",
            f"urn:synthetic:voice-evidence:{suffix}",
        ),
    )
    subject_id, object_id = (row[0] for row in cursor.fetchall())
    cursor.execute(
        """
        insert into provenance_resource_type (resource_id, class_code)
        values (%s, 'prov_entity'), (%s, 'prov_entity')
        """,
        (subject_id, object_id),
    )
    cursor.execute(
        """
        insert into provenance_assertion
            (subject_resource_id, relation_code, object_resource_id)
        values (%s, 'prov_was_derived_from', %s)
        returning assertion_id
        """,
        (subject_id, object_id),
    )
    assertion_id = cursor.fetchone()[0]
    cursor.execute(
        """
        insert into source_post_voice
            (post_id, voice_type_code, is_primary, truth_status_code,
             provenance_assertion_id, effective_from, recorded_at)
        values (%s, %s, false, 'truth_observed', %s, clock_timestamp(), clock_timestamp())
        """,
        (post_id, voice_type_code, assertion_id),
    )


def test_aba_primary_history_matches_api_and_ontology_cutoffs(
    voice_history_dsn: str,
) -> None:
    """A → B → A is recoverable at before / between / after cutoffs."""
    connection = _connect(voice_history_dsn)
    try:
        with connection.cursor() as cursor:
            post_id = _insert_synthetic_post(cursor, "voc")
            cursor.execute(
                "update source_post set voc_type_code = 'vops' where post_id = %s",
                (post_id,),
            )
            cursor.execute("select pg_sleep(0.002)")
            cursor.execute(
                "update source_post set voc_type_code = 'voc' where post_id = %s",
                (post_id,),
            )
            rows = _primary_rows(cursor, post_id)
            assert [(row[0], row[1]) for row in rows] == [
                ("voc", True),
                ("vops", True),
                ("voc", True),
            ]
            first_from, first_to = rows[0][2], rows[0][3]
            second_from, second_to = rows[1][2], rows[1][3]
            third_from, third_to = rows[2][2], rows[2][3]
            assert first_to == second_from
            assert second_to == third_from
            assert third_to is None
            assert first_from < first_to < second_to

            before_first = first_from - timedelta(seconds=1)
            between = second_from + (second_to - second_from) / 2
            after_last = third_from + timedelta(seconds=1)

            assert _api_primary(cursor, post_id, None) == ["voc"]
            assert _api_primary(cursor, post_id, before_first) == []
            assert _api_primary(cursor, post_id, first_from) == ["voc"]
            assert _api_primary(cursor, post_id, between) == ["vops"]
            assert _api_primary(cursor, post_id, second_from) == ["vops"]
            assert _api_primary(cursor, post_id, after_last) == ["voc"]
            assert _api_primary(cursor, post_id, third_from) == ["voc"]

            snapshot_during_b = between
            snapshot_after = after_last
            assert _ontology_primary(cursor, post_id, None, snapshot_during_b) == [
                "vops"
            ]
            assert _ontology_primary(cursor, post_id, None, snapshot_after) == ["voc"]
            assert _ontology_primary(cursor, post_id, first_from, snapshot_after) == [
                "voc"
            ]
            assert _ontology_primary(cursor, post_id, between, snapshot_after) == [
                "vops"
            ]

            cursor.execute(
                """
                update source_post_voice
                   set recorded_at = %s
                 where post_id = %s
                   and is_primary
                   and effective_from = %s
                """,
                (snapshot_after + timedelta(seconds=1), post_id, third_from),
            )
            assert _ontology_primary(cursor, post_id, None, snapshot_after) == []
    finally:
        connection.close()


def test_live_read_returns_exactly_one_current_primary(voice_history_dsn: str) -> None:
    """Live reads use effective_to IS NULL and never two current primaries."""
    connection = _connect(voice_history_dsn)
    try:
        with connection.cursor() as cursor:
            post_id = _insert_synthetic_post(cursor, "voc")
            cursor.execute(
                "update source_post set voc_type_code = 'voe' where post_id = %s",
                (post_id,),
            )
            cursor.execute(
                """
                select voice_type_code
                  from source_post_voice
                 where post_id = %s
                   and is_primary
                   and effective_to is null
                """,
                (post_id,),
            )
            current = [row[0] for row in cursor.fetchall()]
            assert current == ["voe"]
            assert _api_primary(cursor, post_id, None) == ["voe"]
    finally:
        connection.close()


def test_incoming_primary_closes_matching_additional_assignment(
    voice_history_dsn: str,
) -> None:
    """Changing the imported primary to B closes a current additional B first."""
    connection = _connect(voice_history_dsn)
    try:
        with connection.cursor() as cursor:
            post_id = _insert_synthetic_post(cursor, "voc")
            _insert_additional_voice(cursor, post_id, "vops")
            cursor.execute(
                """
                select effective_to
                  from source_post_voice
                 where post_id = %s
                   and voice_type_code = 'vops'
                   and not is_primary
                   and effective_to is null
                """,
                (post_id,),
            )
            assert cursor.fetchone() is not None
            cursor.execute(
                "update source_post set voc_type_code = 'vops' where post_id = %s",
                (post_id,),
            )
            cursor.execute(
                """
                select is_primary, effective_to is null as is_current
                  from source_post_voice
                 where post_id = %s
                   and voice_type_code = 'vops'
                 order by is_primary, effective_from
                """,
                (post_id,),
            )
            additional, new_primary = cursor.fetchall()
            assert additional == (False, False)
            assert new_primary == (True, True)
    finally:
        connection.close()


def test_gist_exclusion_rejects_overlapping_primary_intervals(
    voice_history_dsn: str,
) -> None:
    """PostgreSQL rejects two primary intervals that share an instant."""
    connection = _connect(voice_history_dsn)
    try:
        with connection.cursor() as cursor:
            post_id = _insert_synthetic_post(cursor, "voc")
            cursor.execute(
                """
                select effective_from
                  from source_post_voice
                 where post_id = %s
                   and is_primary
                   and effective_to is null
                """,
                (post_id,),
            )
            opened_at = cursor.fetchone()[0]
            with pytest.raises(
                (psycopg2.errors.ExclusionViolation, psycopg2.errors.RaiseException)
            ):
                cursor.execute(
                    """
                    insert into source_post_voice
                        (post_id, voice_type_code, is_primary, truth_status_code,
                         effective_from, recorded_at)
                    values (%s, 'vops', true, 'truth_observed', %s, clock_timestamp())
                    """,
                    (post_id, opened_at),
                )
    finally:
        connection.close()


def test_concurrent_primary_updates_serialize_non_overlapping_history(
    voice_history_dsn: str,
) -> None:
    """Two concurrent voc_type_code updates leave one current, non-overlapping primary."""
    setup = _connect(voice_history_dsn)
    try:
        with setup.cursor() as cursor:
            post_id = _insert_synthetic_post(cursor, "voc")
    finally:
        setup.close()

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def _update(next_code: str) -> None:
        connection = psycopg2.connect(voice_history_dsn)
        try:
            barrier.wait(timeout=10)
            with connection.cursor() as cursor:
                cursor.execute(
                    "update source_post set voc_type_code = %s where post_id = %s",
                    (next_code, post_id),
                )
            connection.commit()
        except (psycopg2.Error, threading.BrokenBarrierError) as exc:
            errors.append(exc)
            connection.rollback()
        finally:
            connection.close()

    workers = [
        threading.Thread(target=_update, args=("voe",)),
        threading.Thread(target=_update, args=("vops",)),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=30)
        assert not worker.is_alive()
    assert errors == []

    connection = _connect(voice_history_dsn)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select voice_type_code, effective_from, effective_to
                  from source_post_voice
                 where post_id = %s
                   and is_primary
                 order by effective_from
                """,
                (post_id,),
            )
            history = cursor.fetchall()
            assert len(history) == 3
            assert history[0][0] == "voc"
            assert history[-1][2] is None
            assert {history[1][0], history[2][0]} == {"voe", "vops"}
            for index in range(len(history) - 1):
                assert history[index][2] == history[index + 1][1]
                assert history[index][1] < history[index][2]
            cursor.execute(
                """
                select count(*)
                  from source_post_voice
                 where post_id = %s
                   and is_primary
                   and effective_to is null
                """,
                (post_id,),
            )
            assert cursor.fetchone()[0] == 1
            cursor.execute(
                """
                select count(*)
                  from source_post_voice a
                  join source_post_voice b
                    on a.post_id = b.post_id
                   and a.voice_assignment_id < b.voice_assignment_id
                   and a.is_primary
                   and b.is_primary
                   and tstzrange(a.effective_from, a.effective_to, '[)')
                    && tstzrange(b.effective_from, b.effective_to, '[)')
                 where a.post_id = %s
                """,
                (post_id,),
            )
            assert cursor.fetchone()[0] == 0
            live = _api_primary(cursor, post_id, None)
            assert live in (["voe"], ["vops"])
    finally:
        connection.close()


def test_combination_replay_is_replaced_by_history_migration(
    voice_history_dsn: str,
) -> None:
    """migrate.sh filename order must leave the ADR 0252 trigger body installed."""
    connection = _connect(voice_history_dsn)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "select pg_get_functiondef("
                "'synchronize_source_post_primary_voice()'::regprocedure)"
            )
            installed = cursor.fetchone()[0].lower()
            assert "on conflict" not in installed
            assert "is_primary or voice_type_code = new.voc_type_code" in installed
            assert "clock_timestamp()" in installed

        subprocess.run(
            [
                "psql",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                voice_history_dsn,
                "-f",
                str(_COMBINATION_MIGRATION),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "select pg_get_functiondef("
                "'synchronize_source_post_primary_voice()'::regprocedure)"
            )
            reverted = cursor.fetchone()[0].lower()
            assert "on conflict" in reverted
        subprocess.run(
            [
                "psql",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                voice_history_dsn,
                "-f",
                str(_HISTORY_MIGRATION),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "select pg_get_functiondef("
                "'synchronize_source_post_primary_voice()'::regprocedure)"
            )
            restored = cursor.fetchone()[0].lower()
            assert "on conflict" not in restored
            assert "is_primary or voice_type_code = new.voc_type_code" in restored
    finally:
        connection.close()
