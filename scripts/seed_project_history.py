#!/usr/bin/env python3
"""Seed one synthetic full-lifecycle project history after ``make seed``.

The script is idempotent and uses only Demo Corp identities and source posts.
Every event, relation, and responsibility assignment is backed by a synthetic
source post so the Buyer API exercises the production authorization boundary.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2

DEFAULT_POSTGRES_DSN = (
    "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
)
PROJECT_KEY = "P-1042"
PROJECT_NAME = "OO Transformer"
SOURCE_SYSTEM_CODE = "synthetic_project_history"


def _upsert_post(
    cursor,
    *,
    author_account_id: str,
    corporate_entity_id: str,
    event_type_code: str,
    title: str,
    body: str,
    voc_type_code: str,
    created_at: str,
) -> str:
    """Insert or refresh one synthetic evidence post and return its UUID."""

    source_record_key = f"{PROJECT_KEY}:{event_type_code}"
    cursor.execute(
        """
        insert into source_post (
            author_account_id,
            corporate_entity_id,
            post_title,
            post_body,
            voc_type_code,
            visibility_code,
            thread_group_key,
            secondary_grouping_key,
            source_project_code,
            source_project_name,
            source_system_code,
            source_record_key,
            created_at,
            updated_at
        )
        values (%s, %s, %s, %s, %s, 'public', %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (source_system_code, source_record_key)
            where source_system_code is not null and source_record_key is not null
        do update set
            post_title = excluded.post_title,
            post_body = excluded.post_body,
            voc_type_code = excluded.voc_type_code,
            visibility_code = excluded.visibility_code,
            thread_group_key = excluded.thread_group_key,
            secondary_grouping_key = excluded.secondary_grouping_key,
            source_project_code = excluded.source_project_code,
            source_project_name = excluded.source_project_name,
            updated_at = excluded.updated_at
        returning post_id
        """,
        (
            author_account_id,
            corporate_entity_id,
            title,
            body,
            voc_type_code,
            PROJECT_KEY,
            PROJECT_KEY,
            PROJECT_KEY,
            PROJECT_NAME,
            SOURCE_SYSTEM_CODE,
            source_record_key,
            created_at,
            created_at,
        ),
    )
    return str(cursor.fetchone()[0])


def _catalog_person(cursor, person_name: str, role_title: str) -> str:
    """Return one deterministic synthetic cataloged-person UUID."""

    cursor.execute(
        """
        select person_id
          from cataloged_person
         where person_name = %s
         order by created_at, person_id
         limit 1
        """,
        (person_name,),
    )
    row = cursor.fetchone()
    if row is not None:
        return str(row[0])
    cursor.execute(
        """
        insert into cataloged_person
            (person_name, person_side_code, last_known_job_title)
        values (%s, 'our_side', %s)
        returning person_id
        """,
        (person_name, role_title),
    )
    return str(cursor.fetchone()[0])


def seed_project_history(postgres_dsn: str) -> None:
    """Seed five lifecycle events and three evidence-backed responsibility spans."""

    connection = psycopg2.connect(postgres_dsn)
    try:
        with connection.cursor() as cursor:
            migration = (
                Path(__file__).resolve().parents[1]
                / "migrations"
                / "0050_project_history_lifecycle.sql"
            )
            cursor.execute(migration.read_text(encoding="utf-8"))
            cursor.execute(
                """
                select account.user_account_id, entity.corporate_entity_id
                  from user_account account
                  join account_affiliation affiliation
                    on affiliation.user_account_id = account.user_account_id
                  join corporate_entity entity
                    on entity.corporate_entity_id = affiliation.corporate_entity_id
                 where entity.corporate_entity_code = 'DEMO-CORP-01'
                 order by (account.display_name = 'Demo Admin') desc,
                          account.user_account_id
                 limit 1
                """
            )
            identity = cursor.fetchone()
            if identity is None:
                raise RuntimeError("run `make seed` before seeding project history")
            account_id, corporate_entity_id = map(str, identity)

            cursor.execute(
                """
                insert into project_history_project (project_key, project_name)
                values (%s, %s)
                on conflict (project_key) do update set
                    project_name = excluded.project_name,
                    updated_at = now()
                """,
                (PROJECT_KEY, PROJECT_NAME),
            )

            event_specs = (
                ("project_event_order", "Order awarded", "Synthetic order award for OO Transformer.", "vom", "2022-03-14T09:00:00+00:00"),
                ("project_event_spec_change", "Specification revision approved", "Synthetic approved transformer specification revision.", "vom", "2023-06-01T09:00:00+00:00"),
                ("project_event_delivery", "Delivery completed", "Synthetic delivery completion evidence.", "vom", "2024-11-18T09:00:00+00:00"),
                ("project_event_voc", "Insulation performance VOC", "Synthetic field VOC about insulation performance.", "voc", "2026-02-03T09:00:00+00:00"),
                ("project_event_rebid", "Rebid opportunity opened", "Synthetic follow-up rebid opportunity.", "vom", "2026-08-10T09:00:00+00:00"),
            )

            event_ids: dict[str, str] = {}
            post_ids: dict[str, str] = {}
            for event_type, title, body, voc_type, occurred_at in event_specs:
                post_id = _upsert_post(
                    cursor,
                    author_account_id=account_id,
                    corporate_entity_id=corporate_entity_id,
                    event_type_code=event_type,
                    title=title,
                    body=body,
                    voc_type_code=voc_type,
                    created_at=occurred_at,
                )
                post_ids[event_type] = post_id
                cursor.execute(
                    """
                    insert into post_project_mention (
                        post_id, project_key, project_name, evidence_text,
                        confidence, ontology_iri, extraction_method
                    )
                    values (%s, %s, %s, %s, 1.000,
                            'https://contextualwisdomlab.github.io/lineageweave/ontology#Project',
                            'synthetic_explicit_project_seed')
                    on conflict (post_id, project_key) do update set
                        project_name = excluded.project_name,
                        evidence_text = excluded.evidence_text,
                        confidence = excluded.confidence,
                        ontology_iri = excluded.ontology_iri,
                        extraction_method = excluded.extraction_method
                    """,
                    (post_id, PROJECT_KEY, PROJECT_NAME, f"{PROJECT_KEY} {PROJECT_NAME}"),
                )
                cursor.execute(
                    """
                    insert into project_history_event (
                        project_key, event_type_code, event_title,
                        event_start_at, evidence_post_id
                    )
                    values (%s, %s, %s, %s, %s)
                    on conflict (
                        project_key, evidence_post_id, event_type_code, event_start_at
                    ) do update set event_title = excluded.event_title
                    returning project_history_event_id
                    """,
                    (PROJECT_KEY, event_type, title, occurred_at, post_id),
                )
                event_ids[event_type] = str(cursor.fetchone()[0])

            relation_specs = (
                ("project_event_spec_change", "project_event_order", "project_relation_follows", "project_event_spec_change"),
                ("project_event_delivery", "project_event_spec_change", "project_relation_follows", "project_event_delivery"),
                ("project_event_voc", "project_event_delivery", "project_relation_related_to", "project_event_voc"),
                ("project_event_rebid", "project_event_voc", "project_relation_follows", "project_event_rebid"),
            )
            for source_type, target_type, relation_type, evidence_type in relation_specs:
                cursor.execute(
                    """
                    insert into project_event_relation (
                        source_project_history_event_id,
                        target_project_history_event_id,
                        relation_type_code,
                        evidence_post_id,
                        relation_confidence
                    )
                    values (%s, %s, %s, %s, null)
                    on conflict (
                        source_project_history_event_id,
                        target_project_history_event_id,
                        relation_type_code
                    ) do update set evidence_post_id = excluded.evidence_post_id
                    """,
                    (
                        event_ids[source_type],
                        event_ids[target_type],
                        relation_type,
                        post_ids[evidence_type],
                    ),
                )

            people = {
                "sales": _catalog_person(cursor, "Synthetic Sales Owner", "Sales owner"),
                "pm": _catalog_person(cursor, "Synthetic Project Manager", "Project manager"),
                "service": _catalog_person(cursor, "Synthetic Service Owner", "Service owner"),
            }
            assignments = (
                (people["sales"], "project_role_sales", "2022-03-01T00:00:00+00:00", "2023-05-20T00:00:00+00:00", post_ids["project_event_order"]),
                (people["pm"], "project_role_project_manager", "2023-06-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00", post_ids["project_event_spec_change"]),
                (people["service"], "project_role_service", "2026-01-01T00:00:00+00:00", None, post_ids["project_event_voc"]),
            )
            for person_id, role_code, valid_from, valid_to, evidence_post_id in assignments:
                cursor.execute(
                    """
                    insert into project_responsibility_assignment (
                        project_key, cataloged_person_id,
                        responsibility_role_code, valid_from, valid_to,
                        evidence_post_id
                    )
                    values (%s, %s, %s, %s, %s, %s)
                    on conflict (
                        project_key, cataloged_person_id,
                        responsibility_role_code, valid_from
                    ) do update set
                        valid_to = excluded.valid_to,
                        evidence_post_id = excluded.evidence_post_id
                    """,
                    (
                        PROJECT_KEY,
                        person_id,
                        role_code,
                        valid_from,
                        valid_to,
                        evidence_post_id,
                    ),
                )
        connection.commit()
    finally:
        connection.close()


def main() -> None:
    """Parse CLI arguments and seed the synthetic project lifecycle."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--postgres-dsn", default=DEFAULT_POSTGRES_DSN)
    args = parser.parse_args()
    seed_project_history(args.postgres_dsn)


if __name__ == "__main__":
    main()
