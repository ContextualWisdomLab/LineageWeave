"""Live PostgreSQL proof of ADR 0252 primary Voice history.

Skipped unless a local PostgreSQL server is reachable
(LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN), matching tests/test_schema.py.
Synthetic fixtures only: no real organization, person, or record ids.
"""

from __future__ import annotations

import os
import subprocess
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import psycopg2.errors
import pytest

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


def test_aba_primary_history_matches_api_and_ontology_cutoffs(voice_history_dsn: str) -> None:
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
            assert _ontology_primary(cursor, post_id, None, snapshot_during_b) == ["vops"]
            assert _ontology_primary(cursor, post_id, None, snapshot_after) == ["voc"]
            assert _ontology_primary(cursor, post_id, first_from, snapshot_after) == ["voc"]
            assert _ontology_primary(cursor, post_id, between, snapshot_after) == ["vops"]

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
        except Exception as exc:
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
