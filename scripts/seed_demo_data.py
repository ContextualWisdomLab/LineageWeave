#!/usr/bin/env python3
"""Seeds synthetic Phase 1 demo data into the running Postgres/Keycloak
stack, so the whole login -> post-list -> post-detail path is demonstrable
end to end (per ADR 0001: real infrastructure, synthetic content only).

Genuinely real, not fabricated locally and hoped to match: this script logs
into Keycloak's own admin REST API to fetch the actual `sub` (user id) of
the two demo accounts seeded by docker/keycloak/realm-export.json, then
inserts user_account rows in Postgres keyed by those real subject ids --
the same identity Keycloak issues in an access token's `sub` claim, which
is exactly what backend.app.auth looks up. Seeded tickets also ``XADD``
onto Valkey so the Activity panel is not empty after ``make seed``.

HTTP goes through ``lineageweave.http_client`` (http(s) allowlist).

Usage: KEYCLOAK_ADMIN_PASSWORD=... python3 scripts/seed_demo_data.py [--postgres-dsn ...] [--keycloak-base-url ...] [--valkey-url ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import sys
from pathlib import Path
from urllib.parse import urlencode

# Allow `python3 scripts/seed_demo_data.py` from a checkout without install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2

from lineageweave.http_client import get_json, get_json_list, post_form
from lineageweave.post_summary import ACTOR_TYPE_PERSON, POST_SUMMARY_CONTRACT_VERSION
from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable

REALM = "lineageweave-demo"
DEFAULT_POSTGRES_DSN = "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
DEFAULT_KEYCLOAK_BASE_URL = "http://localhost:18080"
DEFAULT_KEYCLOAK_ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN", "admin")
DEFAULT_VALKEY_URL = "redis://localhost:16379/0"

# ADR 0013: one Demo Corp capture, many runs (lineage + TEPP + report).
DEMO_SOURCE_SNAPSHOT_MATERIAL = b"lineageweave-synthetic-demo-snapshot-v1"
DEMO_SOURCE_CONTRACT_VERSION = "demo-source-contract-v1"
DEMO_LINEAGE_IDEMPOTENCY_KEY = "demo-lineage-seed-2026-w02"
DEMO_TEPP_IDEMPOTENCY_KEY = "demo-tepp-seed-2026-w02"
DEMO_TEPP_ACCEPTED_IDEMPOTENCY_KEY = "demo-tepp-accepted-seed-2026-w09"
DEMO_TEPP_ACCEPTED_REMOTE_RUN_ID = "tepp-demo-accepted-run-1"
DEMO_TOPIC_LINEAGE_IDEMPOTENCY_KEY = "demo-topic-lineage-seed-2026-w02"
DEMO_REPORT_IDEMPOTENCY_KEY = "demo-report-seed-2026-w02"

# (post_title, ticket_title, due_date) -- report/calendar fixture tickets.
# Activity seed uses the same titles so Valkey matches.
FIXTURE_TICKET_SPECS = (
    (
        "Pricing renegotiation follow-up",
        "Send Northridge Grid the revised quote",
        "2026-01-12",
    ),
    (
        "Delivery schedule question raised",
        "Confirm the delivery window with logistics",
        "2026-01-16",
    ),
    (
        "Specification revision requested",
        "Send Westfield Power the revised specification",
        "2026-01-14",
    ),
)
CALENDAR_TICKET_TITLE = "Send Riverbend the revised delivery schedule."


def _fetch_demo_user_subjects(base_url: str, admin_user: str, admin_password: str) -> dict[str, str]:
    """Return {username: Keycloak subject id} for the two synthetic demo users."""
    admin_token = post_form(
        f"{base_url}/realms/master/protocol/openid-connect/token",
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": admin_user,
            "password": admin_password,
        },
        timeout=10,
    )["access_token"]

    subjects: dict[str, str] = {}
    for username in ("demo.analyst", "demo.admin"):
        query = urlencode({"username": username, "exact": "true"})
        users = get_json_list(
            f"{base_url}/admin/realms/{REALM}/users?{query}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
            service_peer_name="oidc",
        )
        if not users:
            raise SystemExit(f"Keycloak user '{username}' not found in realm '{REALM}' -- did the realm import run?")
        subjects[username] = users[0]["id"]
    return subjects


def seed(
    postgres_dsn: str,
    subjects: dict[str, str],
    valkey_url: str = DEFAULT_VALKEY_URL,
) -> None:
    """Insert the synthetic corp / role / source_post rows for the demo path."""
    conn = psycopg2.connect(postgres_dsn)
    try:
        with conn.cursor() as cur:
            migrations = Path(__file__).resolve().parents[1] / "migrations"
            cur.execute((migrations / "0002_thread_grouping_keys.sql").read_text())
            cur.execute((migrations / "0003_ticket_commitment_calendar.sql").read_text())
            cur.execute((migrations / "0004_relation_verification.sql").read_text())
            cur.execute((migrations / "0005_post_evaluation.sql").read_text())
            cur.execute((migrations / "0006_report_period_score.sql").read_text())
            cur.execute((migrations / "0007_report_fipc_linking.sql").read_text())
            cur.execute((migrations / "0008_post_summary_result.sql").read_text())
            cur.execute((migrations / "0009_shared_metric_bank.sql").read_text())
            cur.execute((migrations / "0010_report_item_information.sql").read_text())
            cur.execute((migrations / "0011_post_chat_result.sql").read_text())
            cur.execute((migrations / "0012_report_leftover_pair.sql").read_text())
            cur.execute((migrations / "0163_report_leftover_observed_expected.sql").read_text())
            cur.execute((migrations / "0164_report_leftover_map_rank.sql").read_text())
            cur.execute((migrations / "0168_report_leftover_map_coverage.sql").read_text())
            cur.execute((migrations / "0169_report_leftover_map_axis.sql").read_text())
            cur.execute((migrations / "0182_report_leftover_map_unexplained.sql").read_text())
            cur.execute((migrations / "0185_report_leftover_map_cross_share.sql").read_text())
            cur.execute((migrations / "0206_report_leftover_map_reconstruction.sql").read_text())
            cur.execute((migrations / "0233_report_leftover_map_unexplained_share.sql").read_text())
            cur.execute((migrations / "0244_report_leftover_map_explained_share.sql").read_text())
            cur.execute((migrations / "0245_report_leftover_map_coordinates.sql").read_text())
            cur.execute((migrations / "0060_role_responsibility_agent_type.sql").read_text())
            cur.execute((migrations / "0013_person_job_title.sql").read_text())
            cur.execute((migrations / "0014_role_responsibility_team_actor_type.sql").read_text())
            cur.execute((migrations / "0015_organization_name_resolution.sql").read_text())
            cur.execute((migrations / "0016_cross_post_actor_identity.sql").read_text())
            cur.execute((migrations / "0018_analysis_run_registry.sql").read_text())
            cur.execute((migrations / "0019_role_catalog_identity.sql").read_text())
            cur.execute((migrations / "0020_analysis_run_retention_purge.sql").read_text())
            cur.execute((migrations / "0021_analysis_run_reconstruction.sql").read_text())
            cur.execute((migrations / "0022_analysis_source_snapshot_member.sql").read_text())
            cur.execute((migrations / "0023_analysis_run_outbox.sql").read_text())
            cur.execute((migrations / "0131_analysis_run_topic_lineage_kind.sql").read_text())
            cur.execute((migrations / "0024_source_post_revision.sql").read_text())
            cur.execute((migrations / "0025_role_person_catalog_identity.sql").read_text())
            cur.execute((migrations / "0140_post_lineage_interval_relation.sql").read_text())
            cur.execute(
                """
                insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
                    ('corporate_entity_level', 'group', 'Group', 0),
                    ('corporate_entity_level', 'company', 'Company', 1),
                    ('corporate_entity_level', 'plant', 'Plant', 2),
                    ('post_visibility', 'public', 'Public', 0),
                    ('post_visibility', 'private', 'Private', 1),
                    ('voc_type', 'voc', 'Voice of Customer', 0),
                    ('voc_type', 'vocc', 'Voice of Customer''s Customer', 1),
                    ('voc_type', 'voco', 'Voice of Competitor', 2),
                    ('voc_type', 'vom', 'Voice of Market', 3),
                    ('voc_type', 'vop', 'Voice of Partner', 4),
                    ('permission', 'post_read', 'Read posts', 0),
                    ('permission', 'post_admin', 'Administer posts', 1),
                    ('person_side', 'our_side', 'Our side', 0),
                    ('person_side', 'counterparty', 'Counterparty', 1),
                    ('node_type', 'node_person', 'Person', 0),
                    ('node_type', 'node_corporate_entity', 'Corporate entity', 1),
                    ('node_type', 'node_post', 'Post', 2),
                    ('edge_type', 'edge_mention', 'Mentioned in', 0),
                    ('edge_type', 'edge_affiliation', 'Affiliated with', 1),
                    ('edge_type', 'edge_co_mention', 'Co-mentioned', 2),
                    ('entity_relationship_type', 'rel_voc', 'Voice of Customer', 0),
                    ('entity_relationship_type', 'rel_vom', 'Voice of Market', 1),
                    ('entity_relationship_type', 'rel_vop', 'Voice of Partner', 2),
                    ('entity_relationship_type', 'rel_vocc', 'Voice of Customer''s Customer', 3),
                    ('entity_relationship_type', 'rel_voco', 'Voice of Competitor', 4),
                    ('entity_relationship_type', 'rel_vos', 'Voice of Supplier', 5),
                    ('ticket_status', 'open', 'Open', 0),
                    ('ticket_status', 'in_progress', 'In progress', 1),
                    ('ticket_status', 'closed', 'Closed', 2),
                    ('interval_relation', 'interval_before', 'Before', 0),
                    ('interval_relation', 'interval_after', 'After', 1),
                    ('interval_relation', 'interval_meets', 'Meets', 2),
                    ('interval_relation', 'interval_met_by', 'Met by', 3),
                    ('interval_relation', 'interval_overlaps', 'Overlaps', 4),
                    ('interval_relation', 'interval_overlapped_by', 'Overlapped by', 5),
                    ('interval_relation', 'interval_starts', 'Starts', 6),
                    ('interval_relation', 'interval_started_by', 'Started by', 7),
                    ('interval_relation', 'interval_during', 'During', 8),
                    ('interval_relation', 'interval_contains', 'Contains', 9),
                    ('interval_relation', 'interval_finishes', 'Finishes', 10),
                    ('interval_relation', 'interval_finished_by', 'Finished by', 11),
                    ('interval_relation', 'interval_equals', 'Equals', 12)
                on conflict (lookup_code) do nothing
                """
            )

            cur.execute(
                "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
                "values ('DEMO-GROUP', 'Demo Group', 'group') "
                "on conflict (corporate_entity_code) do update set entity_name = excluded.entity_name "
                "returning corporate_entity_id"
            )
            group_entity_id = cur.fetchone()[0]
            cur.execute(
                "insert into corporate_entity (parent_entity_id, corporate_entity_code, entity_name, entity_level_code) "
                "values (%s, 'DEMO-CORP-01', 'Demo Corp', 'company') "
                "on conflict (corporate_entity_code) do update set "
                "entity_name = excluded.entity_name, "
                "entity_level_code = excluded.entity_level_code, "
                "parent_entity_id = excluded.parent_entity_id "
                "returning corporate_entity_id",
                (group_entity_id,),
            )
            corporate_entity_id = cur.fetchone()[0]
            cur.execute(
                """
                insert into organization_name_resolution
                    (raw_organization_name, resolved_organization_name,
                     verification_status_code, verification_evidence_url)
                values ('DC', 'Demo Corp', 'verify_corroborated',
                        'https://example.test/searxng?q=Demo+Corp+DC')
                on conflict (raw_organization_name) do update set
                    resolved_organization_name = excluded.resolved_organization_name,
                    verification_status_code = excluded.verification_status_code,
                    verification_evidence_url = excluded.verification_evidence_url,
                    resolved_at = now()
                """
            )

            cur.execute(
                "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) values "
                "(%s, 'DEMO-PU-A', 'Demo Sales Unit A'), (%s, 'DEMO-PU-HQ', 'Demo Headquarters'), "
                "(%s, 'DEMO-PU-LINEAGE', 'Demo Lineage Thread') "
                "on conflict (process_unit_code) do update set process_unit_name = excluded.process_unit_name "
                "returning process_unit_code, process_unit_id",
                (corporate_entity_id, corporate_entity_id, corporate_entity_id),
            )
            process_units = dict(cur.fetchall())  # {code: id}

            cur.execute(
                "insert into access_role (role_code, role_name) values "
                "('viewer', 'Viewer'), ('admin', 'Admin') "
                "on conflict (role_code) do update set role_name = excluded.role_name "
                "returning role_code, access_role_id"
            )
            roles = dict(cur.fetchall())  # {code: id}

            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_read') "
                "on conflict do nothing",
                (roles["viewer"],),
            )
            cur.execute(
                "insert into role_permission (access_role_id, permission_code) values (%s, 'post_read'), (%s, 'post_admin') "
                "on conflict do nothing",
                (roles["admin"], roles["admin"]),
            )

            demo_users = [
                ("demo.analyst", "Demo Analyst", "demo.analyst@example.test", "DEMO-PU-A", "viewer"),
                ("demo.admin", "Demo Admin", "demo.admin@example.test", "DEMO-PU-HQ", "admin"),
            ]
            account_ids: dict[str, str] = {}
            for username, display_name, email, pu_code, role_code in demo_users:
                cur.execute(
                    "insert into user_account (external_subject_id, display_name, email_address) "
                    "values (%s, %s, %s) "
                    "on conflict (external_subject_id) do update set display_name = excluded.display_name "
                    "returning user_account_id",
                    (subjects[username], display_name, email),
                )
                account_id = cur.fetchone()[0]
                account_ids[username] = account_id

                cur.execute(
                    "insert into account_affiliation (user_account_id, corporate_entity_id, process_unit_id) "
                    "values (%s, %s, %s) on conflict do nothing",
                    (account_id, corporate_entity_id, process_units[pu_code]),
                )
                cur.execute(
                    "insert into account_role_assignment (user_account_id, access_role_id) values (%s, %s) "
                    "on conflict do nothing",
                    (account_id, roles[role_code]),
                )

            demo_public_cutoff_body = (
                "Ada West at Demo Corp followed up with Priya Nair at "
                "Northridge Grid about the delayed shipment."
            )
            demo_public_live_body = (
                "Ada West at Demo Corp revised the delayed-shipment note after "
                "the January cutoff: Priya Nair at Northridge Grid now expects "
                "a later delivery window."
            )
            cur.execute("select post_id, post_body from source_post where post_title = 'Demo public post'")
            demo_public_row = cur.fetchone()
            if demo_public_row is None:
                cur.execute(
                    "insert into source_post (author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, voc_type_code, visibility_code, created_at, updated_at) "
                    "values (%s, %s, %s, 'Demo public post', "
                    "%s, "
                    "'voc', 'public', '2026-01-10T12:00:00Z', '2026-01-10T12:00:00Z') "
                    "returning post_id",
                    (
                        account_ids["demo.analyst"],
                        corporate_entity_id,
                        process_units["DEMO-PU-A"],
                        demo_public_cutoff_body,
                    ),
                )
                demo_public_post_id = cur.fetchone()[0]
                cur.execute(
                    "update source_post set post_body = %s, "
                    "updated_at = '2026-01-13T09:00:00Z' "
                    "where post_id = %s",
                    (demo_public_live_body, demo_public_post_id),
                )
                cur.execute(
                    "insert into source_post (author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, voc_type_code, visibility_code, created_at, updated_at) "
                    "values (%s, %s, %s, 'Demo private post', 'A synthetic private post scoped to Demo Corp accounts.', 'vom', 'private', '2026-01-10T12:00:00Z', '2026-01-10T12:00:00Z')",
                    (account_ids["demo.admin"], corporate_entity_id, process_units["DEMO-PU-HQ"]),
                )
            else:
                demo_public_post_id = demo_public_row[0]
                if demo_public_row[1] != demo_public_live_body:
                    cur.execute(
                        "update source_post set post_body = %s where post_id = %s",
                        (demo_public_live_body, demo_public_post_id),
                    )
                    cur.execute(
                        "update source_post set created_at = '2026-01-10T12:00:00Z' "
                        "where post_id = %s",
                        (demo_public_post_id,),
                    )
            from base64 import b64encode
            from io import BytesIO

            from PIL import Image, ImageDraw

            synthetic_image = Image.new("RGBA", (128, 96), (0, 0, 0, 0))
            ImageDraw.Draw(synthetic_image).rectangle(
                (8, 8, 120, 88), fill=(44, 98, 168, 255)
            )
            image_bytes = BytesIO()
            synthetic_image.save(image_bytes, format="TIFF")
            demo_image_body = (
                '<p>Synthetic raster evidence: '
                '<img alt="Synthetic blue panel" src="data:image/tiff;base64,'
                f'{b64encode(image_bytes.getvalue()).decode("ascii")}"'
                ' /></p>'
            )
            cur.execute(
                "select post_id, post_body from source_post where post_title = 'Demo image post'"
            )
            demo_image_row = cur.fetchone()
            if demo_image_row is None:
                cur.execute(
                    "insert into source_post (author_account_id, corporate_entity_id, process_unit_id, "
                    "post_title, post_body, voc_type_code, visibility_code, created_at, updated_at) "
                    "values (%s, %s, %s, 'Demo image post', %s, 'voc', 'public', "
                    "'2026-01-11T12:00:00Z', '2026-01-11T12:00:00Z')",
                    (
                        account_ids["demo.analyst"],
                        corporate_entity_id,
                        process_units["DEMO-PU-A"],
                        demo_image_body,
                    ),
                )
            elif demo_image_row[1] != demo_image_body:
                cur.execute(
                    "update source_post set post_body = %s where post_id = %s",
                    (demo_image_body, demo_image_row[0]),
                )
            cur.execute(
                """
                insert into source_post_revision (
                    post_id, post_title, post_body, written_at, superseded_at
                )
                select %s, 'Demo public post', %s,
                       '2026-01-10T12:00:00Z', '2026-01-13T09:00:00Z'
                where not exists (
                    select 1 from source_post_revision
                     where post_id = %s
                       and written_at <= '2026-01-12T12:00:00Z'
                       and (superseded_at is null or superseded_at > '2026-01-12T12:00:00Z')
                )
                """,
                (demo_public_post_id, demo_public_cutoff_body, demo_public_post_id),
            )
            cur.execute(
                "update source_post set created_at = '2026-01-10T12:00:00Z', "
                "updated_at = '2026-01-10T12:00:00Z' "
                "where post_title = 'Demo private post'"
            )
            cur.execute(
                "insert into post_counterparty_entity (post_id, counterparty_entity_name, relationship_type_code) "
                "values (%s, 'Northridge Grid', 'rel_voc'), (%s, 'Demo Corp', 'rel_voc') "
                "on conflict do nothing",
                (demo_public_post_id, demo_public_post_id),
            )
            _seed_demo_public_summary(cur, demo_public_post_id)
            _seed_demo_public_chat(cur, demo_public_post_id)
            cur.execute("select person_id from cataloged_person where person_name = 'Ada West'")
            if cur.fetchone() is None:
                from lineageweave.knowledge_graph import knowledge_graph_edges_for_post

                cur.execute(
                    "insert into cataloged_person (person_name, person_side_code, last_known_job_title) values "
                    "('Ada West', 'our_side', 'Account manager'), "
                    "('Priya Nair', 'counterparty', 'Procurement lead') "
                    "returning person_name, person_id"
                )
                people = dict(cur.fetchall())
                cur.execute(
                    "insert into person_affiliation (person_id, affiliated_organization_name, affiliated_corporate_entity_id) "
                    "values (%s, 'Demo Corp', %s)",
                    (people["Ada West"], corporate_entity_id),
                )
                cur.execute(
                    "insert into person_affiliation (person_id, affiliated_organization_name) values "
                    "(%s, 'Northridge Grid'), (%s, 'Northridge Holdings')",
                    (people["Priya Nair"], people["Priya Nair"]),
                )
                cur.execute(
                    "insert into post_person_mention (post_id, person_id) values (%s, %s), (%s, %s)",
                    (demo_public_post_id, people["Ada West"], demo_public_post_id, people["Priya Nair"]),
                )
                for edge in knowledge_graph_edges_for_post(
                    str(demo_public_post_id),
                    [str(people["Ada West"]), str(people["Priya Nair"])],
                    [(str(people["Ada West"]), str(corporate_entity_id))],
                ):
                    cur.execute(
                        "insert into knowledge_graph_edge ("
                        "source_node_type_code, source_node_id, target_node_type_code, "
                        "target_node_id, edge_type_code, edge_weight"
                        ") values (%s, %s, %s, %s, %s, %s)",
                        (
                            edge.source_node_type_code,
                            edge.source_node_id,
                            edge.target_node_type_code,
                            edge.target_node_id,
                            edge.edge_type_code,
                            edge.edge_weight,
                        ),
                    )

            _seed_demo_public_summary(cur, demo_public_post_id)

            _seed_reconstructed_lineage(
                cur,
                account_ids["demo.analyst"],
                corporate_entity_id,
                process_units["DEMO-PU-LINEAGE"],
            )
            _seed_demo_calendar_commitment(
                cur,
                account_ids["demo.analyst"],
                corporate_entity_id,
                process_units["DEMO-PU-LINEAGE"],
            )
            _seed_fixture_keymen_and_voc(cur, corporate_entity_id)
            _seed_fixture_summaries(cur)
            _seed_fixture_chats(cur)
            _seed_fixture_evaluations(cur)
            _seed_fixture_tickets(cur)
            _seed_lineage_interval_relations(cur)
            _seed_fixture_ticket_activity(cur, account_ids["demo.analyst"], valkey_url)
            _seed_demo_period_report(
                cur,
                account_ids["demo.analyst"],
                corporate_entity_id,
                process_units["DEMO-PU-LINEAGE"],
            )
            _seed_demo_analysis_run(
                cur,
                account_ids["demo.analyst"],
                corporate_entity_id,
            )
            _seed_demo_tepp_run(
                cur,
                account_ids["demo.analyst"],
                corporate_entity_id,
            )
            _seed_demo_tepp_accepted_run(
                cur,
                account_ids["demo.analyst"],
                corporate_entity_id,
            )
            _seed_demo_topic_lineage_run(
                cur,
                account_ids["demo.analyst"],
                corporate_entity_id,
            )
            _seed_demo_report_run(
                cur,
                account_ids["demo.analyst"],
                corporate_entity_id,
            )
            # Fixture occurred_at was stored as created_at. Name that instant
            # as the event clock so Global Ask can disclose the event axis
            # without inventing a second date (ADR 0202).
            cur.execute(
                "update source_post set event_occurred_at = created_at "
                "where event_occurred_at is null"
            )

        conn.commit()
    finally:
        conn.close()


def insert_fixture_source_posts(cur, author_account_id, corporate_entity_id, process_unit_id):
    """Insert ``sample_records()`` as ``source_post`` rows seed and rebuild share.

    Writes ``thread_group_key``, ``secondary_grouping_key``,
    ``created_at = occurred_at``, and ``event_occurred_at = occurred_at``
    so a later ``POST /api/lineage/rebuild`` sees the same grouping and
    timeline reconstruct() was designed on, and Global Ask relative-time
    filters can name the event clock (ADR 0202).
    Returns persisted ``Record``s whose ids are the new post UUIDs.
    """
    from datetime import timezone

    from lineageweave.fixtures import sample_records
    from lineageweave.models import Record

    persisted: list[Record] = []
    for rec in sample_records():
        voc_type = "voc" if rec.secondary_key else "vom"
        occurred = rec.occurred_at
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
        cur.execute(
            "insert into source_post "
            "(author_account_id, corporate_entity_id, process_unit_id, "
            " post_title, post_body, voc_type_code, visibility_code, "
            " thread_group_key, secondary_grouping_key, created_at, updated_at, "
            " event_occurred_at) "
            "values (%s, %s, %s, %s, %s, %s, 'public', %s, %s, %s, %s, %s) returning post_id",
            (
                author_account_id,
                corporate_entity_id,
                process_unit_id,
                rec.label,
                rec.label,
                voc_type,
                rec.group_key,
                rec.secondary_key,
                occurred,
                occurred,
                occurred,
            ),
        )
        post_id = str(cur.fetchone()[0])
        persisted.append(
            Record(post_id, rec.group_key, rec.label, rec.occurred_at, rec.secondary_key)
        )
    return persisted


_DEMO_ESTIMATE_CACHE: list = []


def demo_channel_weight_estimate():
    """The demo's fast-mlsirm-estimated fusion weights (ADR 0200 point 1).

    No hand-picked fusion weight exists anywhere, the demo included: the
    seed fits fast-mlsirm's multilevel 2PL over the demo scenario's
    declared generative design and fuses with those estimates (fitted
    once per process; the design is seeded, so the estimate is
    deterministic). When no estimate can be produced the seed stops and
    names the next action instead of inventing weights.
    """
    from lineageweave.channel_weight_estimation import estimate_fixture_channel_weights

    if not _DEMO_ESTIMATE_CACHE:
        _DEMO_ESTIMATE_CACHE.append(estimate_fixture_channel_weights())
    estimate = _DEMO_ESTIMATE_CACHE[0]
    if estimate is None:
        raise SystemExit(
            "make seed estimates its fusion weights with fast-mlsirm and none "
            "could be produced; install fast-mlsirm from the organization "
            "repository, then run make seed again"
        )
    return estimate


def _persist_demo_channel_weights(cur, estimate) -> None:
    """Persist the demo estimate with full provenance (migration 0200).

    Product reconstruction fails closed without an activated estimate;
    seeding the demo estimate keeps POST /api/lineage/rebuild and
    analysis-run start working on a freshly seeded environment. The
    provenance snapshot digest names the demo's declared generative
    design, the honest anchor label applies, and the estimator version
    is the installed fast-mlsirm.
    """
    import uuid as uuid_module
    from datetime import datetime, timezone

    from lineageweave.channel_weight_estimation import fixture_design_digest
    from scripts.estimate_channel_weights import (
        UNANCHORED_METHOD_CODE,
        estimator_version,
    )

    estimation_run_id = str(uuid_module.uuid4())
    version = estimator_version()
    design_digest = fixture_design_digest()
    knowledge_cutoff = datetime.now(timezone.utc)
    cur.execute(
        "delete from lineage_channel_weight "
        "where channel_set_code = 'channel_set_deterministic'"
    )
    for channel, weight in estimate.weights.items():
        cur.execute(
            """
            insert into lineage_channel_weight
                (channel_set_code, channel_code, weight_value,
                 estimation_run_id, estimation_method_code,
                 estimator_version, anchor_method_code,
                 source_snapshot_sha256, sample_pair_count, knowledge_cutoff,
                 estimated_at)
            values ('channel_set_deterministic', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                channel,
                weight,
                estimation_run_id,
                estimate.estimation_method_code,
                version,
                UNANCHORED_METHOD_CODE,
                design_digest,
                estimate.sample_pair_count,
                knowledge_cutoff,
                knowledge_cutoff,
            ),
        )


def _seed_reconstructed_lineage(cur, author_account_id, corporate_entity_id, process_unit_id) -> None:
    """Persist fixtures.sample_records() as source_posts plus reconstruct edges.

    Without this, GET /api/posts/{id}/lineage is empty on a freshly seeded
    demo: the Event Lineage panel has nothing to show even though
    reconstruct() already knows the A-100 fork.
    """
    from lineageweave.fixtures import sample_records
    from lineageweave.lineage_persistence import lineage_edge_specs, lineage_rebuild_spec

    # Idempotency first: a re-seed of an already-seeded database (whose
    # estimate was persisted on the first pass) must not abort just
    # because fast-mlsirm is absent in this environment.
    records = sample_records()
    cur.execute("select 1 from source_post where post_title = %s", (records[0].label,))
    if cur.fetchone() is not None:
        return

    estimate = demo_channel_weight_estimate()
    _persist_demo_channel_weights(cur, estimate)

    persisted = insert_fixture_source_posts(
        cur, author_account_id, corporate_entity_id, process_unit_id
    )
    edges = lineage_edge_specs(persisted, weights=estimate.weights)
    spec = lineage_rebuild_spec(edges, weights=estimate.weights)
    cur.execute("delete from event_lineage_rebuild")
    cur.execute(
        "insert into event_lineage_rebuild "
        "(rebuild_lock, reconstruction_version, generated_at, min_fused_score, candidate_window) "
        "values (true, %s, now(), %s, %s)",
        (spec.reconstruction_version, spec.min_fused_score, spec.candidate_window),
    )
    for signal_code, signal_weight in spec.channel_weights:
        cur.execute(
            "insert into event_lineage_rebuild_channel "
            "(rebuild_lock, signal_code, signal_weight) values (true, %s, %s)",
            (signal_code, signal_weight),
        )
    for edge in edges:
        cur.execute(
            "insert into post_lineage_edge "
            "(parent_post_id, child_post_id, fused_score, interval_relation_code) "
            "values (%s, %s, %s, 'interval_before') on conflict do nothing",
            (edge.parent_id, edge.child_id, edge.fused_score),
        )
    for row in spec.signal_rows:
        cur.execute(
            "insert into post_lineage_edge_signal "
            "(parent_post_id, child_post_id, signal_code, signal_score, signal_weight, signal_contribution) "
            "values (%s, %s, %s, %s, %s, %s) on conflict do nothing",
            (
                row["parent_post_id"],
                row["child_post_id"],
                row["signal_code"],
                row["signal_score"],
                row["signal_weight"],
                row["signal_contribution"],
            ),
        )


def _write_post_summary(cur, post_id, summary) -> None:
    """Replace the stored summary for ``post_id`` (idempotent re-seed)."""
    cur.execute("delete from post_summary_person_mention where post_id = %s", (post_id,))
    cur.execute("delete from post_summary_result where post_id = %s", (post_id,))
    cur.execute(
        "insert into post_summary_result "
        "(post_id, korean_summary, summary_contract_version) values (%s, %s, %s)",
        (post_id, summary.korean_summary, POST_SUMMARY_CONTRACT_VERSION),
    )
    for ordinal, event_text in enumerate(summary.key_events):
        cur.execute(
            "insert into post_summary_event (post_id, event_ordinal, event_text) values (%s, %s, %s)",
            (post_id, ordinal, event_text),
        )
    for role in summary.roles_and_responsibilities:
        cataloged_person_id = None
        if role.actor_type_code == ACTOR_TYPE_PERSON:
            cur.execute(
                "select person_id from cataloged_person "
                "where person_name = %s "
                "order by created_at, person_id limit 1",
                (role.actor_name,),
            )
            person_row = cur.fetchone()
            if person_row is not None:
                cataloged_person_id = str(person_row[0])
        cur.execute(
            "insert into post_summary_role "
            "(post_id, actor_name, responsibility, actor_type_code, "
            "affiliated_organization_name, cataloged_person_id) "
            "values (%s, %s, %s, %s, %s, %s)",
            (
                post_id,
                role.actor_name,
                role.responsibility,
                role.actor_type_code,
                role.affiliated_organization_name,
                cataloged_person_id,
            ),
        )
        if cataloged_person_id is not None:
            cur.execute(
                "insert into post_summary_person_mention (post_id, person_id) "
                "values (%s, %s) on conflict do nothing",
                (post_id, cataloged_person_id),
            )


def _write_post_chat(cur, post_id, question: str, chat) -> None:
    """Replace the stored Ask exchange for ``(post_id, question)``."""
    from lineageweave.post_chat import normalize_chat_question

    norm = normalize_chat_question(question)
    cur.execute(
        "delete from post_chat_result where post_id = %s and question_norm = %s",
        (post_id, norm),
    )
    cur.execute(
        "insert into post_chat_result (post_id, question_norm, question_text, answer_text) "
        "values (%s, %s, %s, %s)",
        (post_id, norm, question, chat.answer_text),
    )
    seen: set[str] = set()
    ordinal = 0
    for title in chat.cited_titles:
        if title in seen:
            continue
        cur.execute("select post_id from source_post where post_title = %s", (title,))
        cited = cur.fetchone()
        if cited is None:
            continue
        cited_id = cited[0]
        if str(cited_id) in seen:
            continue
        seen.add(title)
        seen.add(str(cited_id))
        cur.execute(
            "insert into post_chat_citation "
            "(post_id, question_norm, citation_ordinal, cited_post_id) "
            "values (%s, %s, %s, %s)",
            (post_id, norm, ordinal, cited_id),
        )
        ordinal += 1


def _seed_demo_public_chat(cur, post_id) -> None:
    """Write the popup Ask answers for the demo public post.

    Idempotent: re-seed replaces the same rows so GET/POST chat stay
    non-empty without a live orchestrator. Writes the canned
    questions so the chips are not a single prompt.
    """
    from backend.app.post_chat_ingestion import seeded_demo_exchanges

    for question, chat in seeded_demo_exchanges():
        _write_post_chat(cur, post_id, question, chat)


def _seed_fixture_chats(cur) -> None:
    """Write Ask answers for A-100/B-200 reconstruct posts and Calendar.

    Event Lineage click-through stays an empty Ask box without this
    when the orchestrator is off. Idempotent -- finds existing titles
    so a re-seed after the lineage insert's early-return still fills
    the popup. Writes the canned questions per fixture.
    """
    from lineageweave.fixtures import ambiguous_commitment_post, sample_records
    from backend.app.post_chat_ingestion import seeded_fixture_exchanges

    titles = [rec.label for rec in sample_records()]
    titles.append(ambiguous_commitment_post()[0])
    for title in titles:
        exchanges = seeded_fixture_exchanges(title)
        if not exchanges:
            continue
        cur.execute("select post_id from source_post where post_title = %s", (title,))
        row = cur.fetchone()
        if row is None:
            continue
        for question, chat in exchanges:
            _write_post_chat(cur, row[0], question, chat)


def _seed_demo_public_summary(cur, post_id) -> None:
    """Write the popup summary for the demo public post.

    Idempotent: re-seed replaces the same row so GET /api/posts/{id}/summary
    stays non-empty without a live orchestrator.
    """
    from backend.app.post_summary_ingestion import seeded_demo_summary

    _write_post_summary(cur, post_id, seeded_demo_summary())


def _seed_fixture_summaries(cur) -> None:
    """Write Korean summaries for A-100/B-200 reconstruct posts and Calendar.

    Event Lineage click-through and the calendar commitment stay empty
    without this: those posts have only their English title as body, and
    GET /api/posts/{id}/summary 503s when the orchestrator is off.
    A-100/B-200 casts also get R&R (Ada West / Priya Nair / Jordan Hale)
    so the popup R&R list is not empty. rec-006 and Calendar stay
    role-less. Idempotent -- finds existing titles so a re-seed after
    the lineage insert's early-return still fills the popup.
    """
    from lineageweave.fixtures import ambiguous_commitment_post, sample_records
    from backend.app.post_summary_ingestion import seeded_fixture_summary

    titles = [rec.label for rec in sample_records()]
    titles.append(ambiguous_commitment_post()[0])
    for title in titles:
        summary = seeded_fixture_summary(title)
        if summary is None:
            continue
        cur.execute("select post_id from source_post where post_title = %s", (title,))
        row = cur.fetchone()
        if row is None:
            continue
        _write_post_summary(cur, row[0], summary)


def constructed_evaluation_categories(title: str) -> dict[str, int]:
    """Deterministic rubric cells from a synthetic title -- not an LLM judge.

    Thetas still come only from ``calibrate_period_report``. These cells
    exist so GET /api/posts/{id}/evaluation is not empty after ``make seed``.
    """
    from lineageweave.post_evaluation import CRITERION_CODES

    lower = title.lower()
    if "unrelated" in lower or "annual account" in lower:
        cats = (1, 2, 0)
    elif "quote" in lower or "approved" in lower or "confirmed" in lower:
        cats = (4, 0, 4)
    elif "delayed" in lower or "shipment" in lower or "follow-up" in lower:
        cats = (2, 3, 3)
    else:
        cats = (2, 1, 2)
    return dict(zip(CRITERION_CODES, cats, strict=True))


def _seed_fixture_evaluations(cur) -> None:
    """Write constructed IRT categories for demo + A-100/B-200 + calendar posts.

    Without this, the Post quality panel is ``Not yet evaluated`` after
    ``make seed`` -- only the dedicated report-band posts have cells.
    Idempotent: existing (post, criterion, rubric) rows are left alone.
    """
    from lineageweave.fixtures import ambiguous_commitment_post, sample_records
    from lineageweave.post_evaluation import RUBRIC_VERSION

    titles = ["Demo public post", ambiguous_commitment_post()[0]]
    titles.extend(rec.label for rec in sample_records())
    for title in titles:
        cur.execute("select post_id from source_post where post_title = %s", (title,))
        row = cur.fetchone()
        if row is None:
            continue
        post_id = row[0]
        for code, category in constructed_evaluation_categories(title).items():
            cur.execute(
                "insert into post_evaluation_response "
                "(post_id, criterion_code, rubric_version, response_category) "
                "values (%s, %s, %s, %s) on conflict do nothing",
                (post_id, code, RUBRIC_VERSION, category),
            )


def _ensure_demo_people(cur, corporate_entity_id) -> dict[str, str]:
    """Ada West / Priya Nair / Jordan Hale plus their affiliations. Idempotent."""
    people: dict[str, str] = {}
    for name, side, title in (
        ("Ada West", "our_side", "Account manager"),
        ("Priya Nair", "counterparty", "Procurement lead"),
        ("Jordan Hale", "our_side", "Bid coordinator"),
    ):
        cur.execute("select person_id from cataloged_person where person_name = %s", (name,))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "insert into cataloged_person (person_name, person_side_code, last_known_job_title) "
                "values (%s, %s, %s) returning person_id",
                (name, side, title),
            )
            people[name] = str(cur.fetchone()[0])
        else:
            people[name] = str(row[0])
            cur.execute(
                "update cataloged_person set last_known_job_title = coalesce(last_known_job_title, %s) "
                "where person_id = %s",
                (title, people[name]),
            )
    cur.execute(
        "insert into person_affiliation "
        "(person_id, affiliated_organization_name, affiliated_corporate_entity_id) "
        "values (%s, 'Demo Corp', %s) on conflict do nothing",
        (people["Ada West"], corporate_entity_id),
    )
    cur.execute(
        "insert into person_affiliation (person_id, affiliated_organization_name) "
        "values (%s, 'Northridge Grid') on conflict do nothing",
        (people["Priya Nair"],),
    )
    cur.execute(
        "insert into person_affiliation (person_id, affiliated_organization_name) "
        "values (%s, 'Northridge Holdings') on conflict do nothing",
        (people["Priya Nair"],),
    )
    cur.execute(
        "insert into person_affiliation "
        "(person_id, affiliated_organization_name, affiliated_corporate_entity_id) "
        "values (%s, 'Demo Corp', %s) on conflict do nothing",
        (people["Jordan Hale"], corporate_entity_id),
    )
    return people


def _seed_fixture_keymen_and_voc(cur, corporate_entity_id) -> None:
    """Attach Keymen, affiliate orgs, and VOC counterparties to fixture posts.

    Event Lineage click-through otherwise shows empty Keyman / affiliate
    / VOC panels: sample_records bodies are the English title only.
    Idempotent -- mentions and counterparties use ON CONFLICT DO NOTHING.
    """
    from lineageweave.fixtures import (
        ambiguous_commitment_post,
        fixture_thread_cast,
        sample_records,
    )
    from lineageweave.knowledge_graph import knowledge_graph_edges_for_post

    people = _ensure_demo_people(cur, corporate_entity_id)
    titles = [rec.label for rec in sample_records()]
    titles.append(ambiguous_commitment_post()[0])
    for title in titles:
        cast = fixture_thread_cast(title)
        if cast is None:
            continue
        cur.execute("select post_id from source_post where post_title = %s", (title,))
        row = cur.fetchone()
        if row is None:
            continue
        post_id = str(row[0])
        if cast.body is not None:
            cur.execute(
                "update source_post set post_body = %s where post_id = %s",
                (cast.body, post_id),
            )
        mentioned: list[str] = []
        for name in cast.person_names:
            person_id = people[name]
            cur.execute(
                "insert into post_person_mention (post_id, person_id) "
                "values (%s, %s) on conflict do nothing",
                (post_id, person_id),
            )
            mentioned.append(person_id)
        if mentioned:
            affiliations = [
                (people[name], str(corporate_entity_id))
                for name in cast.person_names
                if name in people and name != "Priya Nair"
            ]
            for edge in knowledge_graph_edges_for_post(post_id, mentioned, affiliations):
                cur.execute(
                    "select 1 from knowledge_graph_edge where "
                    "source_node_type_code = %s and source_node_id = %s "
                    "and target_node_type_code = %s and target_node_id = %s "
                    "and edge_type_code = %s",
                    (
                        edge.source_node_type_code,
                        edge.source_node_id,
                        edge.target_node_type_code,
                        edge.target_node_id,
                        edge.edge_type_code,
                    ),
                )
                if cur.fetchone() is not None:
                    continue
                cur.execute(
                    "insert into knowledge_graph_edge ("
                    "source_node_type_code, source_node_id, target_node_type_code, "
                    "target_node_id, edge_type_code, edge_weight"
                    ") values (%s, %s, %s, %s, %s, %s)",
                    (
                        edge.source_node_type_code,
                        edge.source_node_id,
                        edge.target_node_type_code,
                        edge.target_node_id,
                        edge.edge_type_code,
                        edge.edge_weight,
                    ),
                )
        cur.execute(
            "insert into post_counterparty_entity "
            "(post_id, counterparty_entity_name, relationship_type_code) "
            "values (%s, %s, %s) on conflict do nothing",
            (post_id, cast.organization_name, cast.relationship_type_code),
        )


def _seed_demo_calendar_commitment(cur, author_account_id, corporate_entity_id, process_unit_id) -> None:
    """Put one dated synthetic commitment on the calendar after `make seed`.

    Without this, GET /api/calendar is empty on a freshly seeded stack --
    the home-page Calendar panel the 0.18.0 work added has nothing to
    show until someone clicks Derive. The post is
    fixtures.ambiguous_commitment_post (relative "by next Friday",
    created_at 2026-01-05) so Derive against DCT still resolves to
    2026-01-09 if an admin re-runs it.
    """
    from datetime import timezone

    from lineageweave.fixtures import (
        ambiguous_commitment_post,
        calendar_commitment_occurred_at,
    )

    title, body = ambiguous_commitment_post()
    cur.execute("select post_id from source_post where post_title = %s", (title,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "insert into source_post "
            "(author_account_id, corporate_entity_id, process_unit_id, "
            " post_title, post_body, voc_type_code, visibility_code, "
            " thread_group_key, created_at) "
            "values (%s, %s, %s, %s, %s, 'voc', 'public', 'A-100', %s) "
            "returning post_id",
            (
                author_account_id,
                corporate_entity_id,
                process_unit_id,
                title,
                body,
                calendar_commitment_occurred_at().replace(tzinfo=timezone.utc),
            ),
        )
        post_id = cur.fetchone()[0]
    else:
        post_id = row[0]

    cur.execute(
        "select 1 from issue_ticket where post_id = %s and commitment_summary is not null",
        (post_id,),
    )
    if cur.fetchone() is not None:
        return
    cur.execute(
        "insert into issue_ticket "
        "(post_id, ticket_status_code, ticket_title, due_date, commitment_summary) "
        "values (%s, 'open', %s, %s, %s)",
        (
            post_id,
            CALENDAR_TICKET_TITLE,
            "2026-01-09",
            CALENDAR_TICKET_TITLE,
        ),
    )


def _seed_fixture_tickets(cur) -> None:
    """Open tickets on Event Lineage posts a report-member click opens.

    Without this, GET /api/posts/{id}/tickets is empty after ``make seed``
    even though the post already has lineage, Keyman, and evaluation.
    Dated rows also appear on GET /api/calendar (A-100 pricing due
    2026-01-12, B-200 revision due 2026-01-14) so home Calendar is
    not only the Riverbend commitment. Idempotent: a matching ticket
    title on that post is left alone.
    """
    for post_title, ticket_title, due_date in FIXTURE_TICKET_SPECS:
        cur.execute("select post_id from source_post where post_title = %s", (post_title,))
        row = cur.fetchone()
        if row is None:
            continue
        post_id = row[0]
        cur.execute(
            "select 1 from issue_ticket where post_id = %s and ticket_title = %s",
            (post_id, ticket_title),
        )
        if cur.fetchone() is not None:
            continue
        cur.execute(
            "insert into issue_ticket "
            "(post_id, ticket_status_code, ticket_title, due_date) "
            "values (%s, 'open', %s, %s)",
            (post_id, ticket_title, due_date),
        )


def _seed_lineage_interval_relations(cur) -> None:
    """Name Allen relations from observed post creation-day points (ADR 0161)."""
    from lineageweave.interval_relation import (
        allen_interval_relation,
        interval_from_post,
    )

    cur.execute(
        """
        select edge.parent_post_id, edge.child_post_id,
               parent_post.created_at, child_post.created_at
          from post_lineage_edge as edge
          join source_post as parent_post on parent_post.post_id = edge.parent_post_id
          join source_post as child_post on child_post.post_id = edge.child_post_id
        """
    )
    rows = list(cur.fetchall())
    for parent_id, child_id, parent_created, child_created in rows:
        code = allen_interval_relation(
            interval_from_post(parent_created),
            interval_from_post(child_created),
        )
        cur.execute(
            "update post_lineage_edge set interval_relation_code = %s "
            "where parent_post_id = %s and child_post_id = %s",
            (code, parent_id, child_id),
        )



def _seed_fixture_ticket_activity(cur, actor_account_id, valkey_url: str) -> None:
    """``XADD`` ticket_created onto each seeded ticket's post stream.

    Without this, GET /api/posts/{id}/activity is empty after ``make seed``
    even though the ticket row exists -- Activity reads Valkey, not
    Postgres. Idempotent: a matching summary on that stream is left alone.
    """
    try:
        import redis
    except ImportError as exc:
        raise SystemExit(
            "redis is required to seed activity events; install with pip install -e '.[dev,backend]'"
        ) from exc

    from backend.app.activity_stream import (
        publish_activity_event_sync,
        ticket_created_summary,
    )
    from lineageweave.fixtures import ambiguous_commitment_post

    specs = [(title, ticket) for title, ticket, _due in FIXTURE_TICKET_SPECS]
    specs.append((ambiguous_commitment_post()[0], CALENDAR_TICKET_TITLE))

    client = None
    try:
        client = redis.from_url(valkey_url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        for post_title, ticket_title in specs:
            cur.execute("select post_id from source_post where post_title = %s", (post_title,))
            row = cur.fetchone()
            if row is None:
                continue
            cur.execute(
                "select 1 from issue_ticket where post_id = %s and ticket_title = %s",
                (row[0], ticket_title),
            )
            if cur.fetchone() is None:
                continue
            publish_activity_event_sync(
                client,
                str(row[0]),
                "ticket_created",
                str(actor_account_id),
                ticket_created_summary(ticket_title),
            )
    except redis.RedisError as exc:
        raise SystemExit(
            f"Valkey at {valkey_url} is unreachable -- did you run `make up`? ({exc})"
        ) from exc
    finally:
        if client is not None:
            client.close()


def _fixture_eval_members(
    cur, period_code: str
) -> dict[str, tuple[list[str], list[tuple[str, str, int]]]]:
    """IRT cells for Event Lineage / calendar fixtures in ``period_code``.

    Dummy high/low band posts stay in ``_ensure_eval_posts``. This only
    returns reconstruct and calendar titles so the seeded report can
    click through to A-100/B-200 DAG posts.
    """
    from lineageweave.fixtures import fixture_titles_in_iso_week
    from lineageweave.post_evaluation import RUBRIC_VERSION

    titles = list(fixture_titles_in_iso_week(period_code))
    if not titles:
        return {}
    cur.execute(
        "select post_id, thread_group_key from source_post "
        "where post_title = any(%s) "
        "and to_char(created_at at time zone 'UTC', 'IYYY-\"W\"IW') = %s",
        (titles, period_code),
    )
    grouped: dict[str, tuple[list[str], list[tuple[str, str, int]]]] = {}
    for post_id, thread_group_key in cur.fetchall():
        key = (thread_group_key or "").strip()
        if not key:
            continue
        cur.execute(
            "select criterion_code, response_category from post_evaluation_response "
            "where post_id = %s and rubric_version = %s",
            (post_id, RUBRIC_VERSION),
        )
        cells = [(str(post_id), code, category) for code, category in cur.fetchall()]
        if not cells:
            continue
        ids, rows = grouped.setdefault(key, ([], []))
        ids.append(str(post_id))
        rows.extend(cells)
    return grouped


def _ensure_eval_posts(
    cur,
    author_account_id,
    corporate_entity_id,
    process_unit_id,
    title_prefix: str,
    category: int,
    created,
    count: int = 4,
    thread_group_key: str | None = None,
) -> tuple[list[str], list[tuple[str, str, int]]]:
    """Insert constructed evaluation posts if missing; always return cells."""
    from lineageweave.post_evaluation import CRITERION_CODES, RUBRIC_VERSION

    post_ids: list[str] = []
    cells: list[tuple[str, str, int]] = []
    for idx in range(count):
        title = f"{title_prefix} {idx}"
        cur.execute("select post_id from source_post where post_title = %s", (title,))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "insert into source_post "
                "(author_account_id, corporate_entity_id, process_unit_id, "
                " post_title, post_body, voc_type_code, visibility_code, "
                " thread_group_key, created_at) "
                "values (%s, %s, %s, %s, 'body', 'voc', 'public', %s, %s) returning post_id",
                (
                    author_account_id,
                    corporate_entity_id,
                    process_unit_id,
                    title,
                    thread_group_key,
                    created,
                ),
            )
            post_id = str(cur.fetchone()[0])
            for code in CRITERION_CODES:
                cur.execute(
                    "insert into post_evaluation_response "
                    "(post_id, criterion_code, rubric_version, response_category) "
                    "values (%s, %s, %s, %s)",
                    (post_id, code, RUBRIC_VERSION, category),
                )
        else:
            post_id = str(row[0])
            if thread_group_key is not None:
                cur.execute(
                    "update source_post set thread_group_key = %s "
                    "where post_id = %s and thread_group_key is null",
                    (thread_group_key, post_id),
                )
        post_ids.append(post_id)
        for code in CRITERION_CODES:
            cells.append((post_id, code, category))
    return post_ids, cells


def _persist_seed_period_report(
    cur, grouping_kind: str, grouping_key: str, period_code: str, report
) -> None:
    """Write one seeded report plus its item bank (idempotent replace)."""
    from lineageweave.post_evaluation import RUBRIC_VERSION

    cur.execute(
        "delete from report_period_score "
        "where grouping_kind = %s and grouping_key = %s "
        "and period_code = %s and rubric_version = %s",
        (grouping_kind, grouping_key, period_code, RUBRIC_VERSION),
    )
    cur.execute(
        "insert into report_period_score ("
        "grouping_kind, grouping_key, period_code, rubric_version, "
        "selected_model, mean_theta, mean_theta_sd, post_count, item_count, "
        "fit_loglik, fit_converged, calibration_score, "
        "link_method, anchor_period_code, delta_mean_theta"
        ") values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            grouping_kind,
            grouping_key,
            period_code,
            RUBRIC_VERSION,
            report.selected_model,
            report.mean_theta,
            report.mean_theta_sd,
            report.post_count,
            report.item_count,
            report.fit_loglik,
            report.fit_converged,
            report.calibration_score,
            report.link_method,
            report.anchor_period_code,
            report.delta_mean_theta,
        ),
    )
    for member in report.member_scores:
        cur.execute(
            "insert into report_member_score ("
            "grouping_kind, grouping_key, period_code, rubric_version, "
            "post_id, theta_eap, theta_sd"
            ") values (%s,%s,%s,%s,%s,%s,%s)",
            (
                grouping_kind,
                grouping_key,
                period_code,
                RUBRIC_VERSION,
                member.post_id,
                member.theta_eap,
                member.theta_sd,
            ),
        )
    bank = report.item_bank
    for index, item_code in enumerate(bank.item_codes):
        cur.execute(
            "insert into report_item_parameter ("
            "grouping_kind, grouping_key, period_code, rubric_version, "
            "item_code, item_index, slope, cat_params"
            ") values (%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                grouping_kind,
                grouping_key,
                period_code,
                RUBRIC_VERSION,
                item_code,
                index,
                bank.slope[index],
                list(bank.cat_params[index]),
            ),
        )
    for item in report.selected_items:
        cur.execute(
            "insert into report_item_information ("
            "grouping_kind, grouping_key, period_code, rubric_version, "
            "item_code, item_rank, information"
            ") values (%s,%s,%s,%s,%s,%s,%s)",
            (
                grouping_kind,
                grouping_key,
                period_code,
                RUBRIC_VERSION,
                item.item_code,
                item.rank,
                item.information,
            ),
        )
    for pair in report.leftover_pairs:
        cur.execute(
            "insert into report_leftover_pair ("
            "grouping_kind, grouping_key, period_code, rubric_version, "
            "pair_kind, post_id, criterion_code, leftover_distance, leftover_residual, "
            "observed_response, expected_response, leftover_map_rank, "
            "leftover_map_unexplained, leftover_map_cross_share, "
            "leftover_map_reconstruction, leftover_map_unexplained_share, "
            "leftover_map_explained_share, leftover_map_person_axis_1, "
            "leftover_map_person_axis_2, leftover_map_item_axis_1, "
            "leftover_map_item_axis_2"
            ") values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                grouping_kind,
                grouping_key,
                period_code,
                RUBRIC_VERSION,
                pair.pair_kind,
                pair.post_id,
                pair.criterion_code,
                pair.leftover_distance,
                pair.leftover_residual,
                pair.observed_response,
                pair.expected_response,
                pair.leftover_map_rank,
                pair.leftover_map_unexplained,
                pair.leftover_map_cross_share,
                pair.leftover_map_reconstruction,
                pair.leftover_map_unexplained_share,
                pair.leftover_map_explained_share,
                pair.leftover_map_person_axis_1,
                pair.leftover_map_person_axis_2,
                pair.leftover_map_item_axis_1,
                pair.leftover_map_item_axis_2,
            ),
        )
    for axis in report.leftover_map_axes:
        cur.execute(
            "insert into report_leftover_map_axis ("
            "grouping_kind, grouping_key, period_code, rubric_version, "
            "axis_index, leftover_singular_value, leftover_share"
            ") values (%s,%s,%s,%s,%s,%s,%s)",
            (
                grouping_kind,
                grouping_key,
                period_code,
                RUBRIC_VERSION,
                axis.axis_index,
                axis.leftover_singular_value,
                axis.leftover_share,
            ),
        )
    if report.leftover_map_coverage is not None:
        coverage = report.leftover_map_coverage
        cur.execute(
            "insert into report_leftover_map_coverage ("
            "grouping_kind, grouping_key, period_code, rubric_version, "
            "map_post_count, scored_post_count, map_item_count, scored_item_count, "
            "incomplete_post_count, incomplete_item_count"
            ") values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                grouping_kind,
                grouping_key,
                period_code,
                RUBRIC_VERSION,
                coverage.map_post_count,
                coverage.scored_post_count,
                coverage.map_item_count,
                coverage.scored_item_count,
                coverage.incomplete_post_count,
                coverage.incomplete_item_count,
            ),
        )


def _seed_demo_period_report(cur, author_account_id, corporate_entity_id, process_unit_id) -> None:
    """Insert two process units on one shared metric, plus a linked W03.

    High-band and low-band posts live in different process units. A
    pooled free-calibrate writes the shared bank; each unit is then
    FIPC-scored so the buyer can compare them. W03 is all-high on the
    high unit. Categories are constructed; thetas come only from
    ``score_groups_on_shared_metric``. A-100 fixtures (and the
    Riverbend calendar post) fold into the high unit; B-200 fixtures
    fold into the low unit. Report members with Event Lineage +
    Keyman + evaluation sort first so a member click is not a dummy
    band row.
    """
    from datetime import datetime, timezone

    from lineageweave.period_report import score_groups_on_shared_metric
    from lineageweave.post_evaluation import IRT_CATEGORY_COUNT

    w02 = "2026-W02"
    w03 = "2026-W03"
    high = IRT_CATEGORY_COUNT - 1
    high_key = str(process_unit_id)

    cur.execute(
        "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) "
        "values (%s, 'DEMO-PU-REPORT-LOW', 'Demo Report Low') "
        "on conflict (process_unit_code) do update set process_unit_name = excluded.process_unit_name "
        "returning process_unit_id",
        (corporate_entity_id,),
    )
    low_unit_id = cur.fetchone()[0]
    low_key = str(low_unit_id)

    w02_high_ids, w02_high_cells = _ensure_eval_posts(
        cur,
        author_account_id,
        corporate_entity_id,
        process_unit_id,
        "High-band period report post",
        high,
        datetime(2026, 1, 5, tzinfo=timezone.utc),
        thread_group_key="A-100",
    )
    w02_low_ids, w02_low_cells = _ensure_eval_posts(
        cur,
        author_account_id,
        corporate_entity_id,
        low_unit_id,
        "Low-band period report post",
        0,
        datetime(2026, 1, 5, tzinfo=timezone.utc),
        thread_group_key="B-200",
    )
    w03_ids, w03_cells = _ensure_eval_posts(
        cur,
        author_account_id,
        corporate_entity_id,
        process_unit_id,
        "High-band week-3 period report post",
        high,
        datetime(2026, 1, 12, tzinfo=timezone.utc),
        count=6,
        thread_group_key="A-100",
    )

    w02_fixtures = _fixture_eval_members(cur, w02)
    w03_fixtures = _fixture_eval_members(cur, w03)
    a100_ids, a100_cells = w02_fixtures.get("A-100", ([], []))
    b200_ids, b200_cells = w02_fixtures.get("B-200", ([], []))
    fixture_ids = a100_ids + b200_ids
    fixture_cells = a100_cells + b200_cells
    w03_fixture_ids: list[str] = []
    w03_fixture_cells: list[tuple[str, str, int]] = []
    for extra_ids, extra_cells in w03_fixtures.values():
        w03_fixture_ids.extend(extra_ids)
        w03_fixture_cells.extend(extra_cells)

    bank_report, scored = score_groups_on_shared_metric(
        {
            high_key: (w02_high_ids + a100_ids, w02_high_cells + a100_cells),
            low_key: (w02_low_ids + b200_ids, w02_low_cells + b200_cells),
        },
        source_period_code=w02,
    )
    if bank_report is not None:
        _persist_seed_period_report(cur, "shared_metric", "all", w02, bank_report)
    for grouping_key, report in scored.items():
        _persist_seed_period_report(cur, "process_unit", grouping_key, w02, report)

    bank = (bank_report or next(iter(scored.values()))).item_bank
    _, corp_scored = score_groups_on_shared_metric(
        {
            str(corporate_entity_id): (
                w02_high_ids + w02_low_ids + fixture_ids,
                w02_high_cells + w02_low_cells + fixture_cells,
            )
        },
        item_bank=bank,
        source_period_code=w02,
    )
    for grouping_key, report in corp_scored.items():
        _persist_seed_period_report(cur, "corporate_entity", grouping_key, w02, report)
    _, thread_scored = score_groups_on_shared_metric(
        {
            "A-100": (w02_high_ids + a100_ids, w02_high_cells + a100_cells),
            "B-200": (w02_low_ids + b200_ids, w02_low_cells + b200_cells),
        },
        item_bank=bank,
        source_period_code=w02,
    )
    for grouping_key, report in thread_scored.items():
        _persist_seed_period_report(cur, "thread_group", grouping_key, w02, report)

    high_w02 = scored[high_key]
    _, week3 = score_groups_on_shared_metric(
        {high_key: (w03_ids + w03_fixture_ids, w03_cells + w03_fixture_cells)},
        item_bank=high_w02.item_bank,
        previous_means={high_key: high_w02.mean_theta},
        source_period_code=w03,
    )
    _persist_seed_period_report(cur, "process_unit", high_key, w03, week3[high_key])


def demo_source_snapshot_sha256() -> str:
    """Return the reusable Demo Corp snapshot digest (never a source row)."""
    return hashlib.sha256(DEMO_SOURCE_SNAPSHOT_MATERIAL).hexdigest()


def _ensure_demo_source_snapshot(cur):
    """Return the shared Demo Corp capture, inserting it on first seed.

    Lineage, TEPP, and period-report runs share this snapshot
    (ADR 0013: one capture, many runs). The digest is a hash of a
    fixed demo contract string -- never a source row or DSN.
    """
    digest = demo_source_snapshot_sha256()
    cur.execute(
        "select analysis_source_snapshot_id from analysis_source_snapshot "
        "where snapshot_sha256 = %s",
        (digest,),
    )
    snapshot_row = cur.fetchone()
    if snapshot_row is not None:
        return snapshot_row[0]
    cur.execute(
        """
        insert into analysis_source_snapshot
            (snapshot_sha256, source_contract_version,
             maximum_available_time, captured_at)
        values (%s, %s,
                '2026-01-12T00:00:00Z', '2026-01-12T00:05:00Z')
        returning analysis_source_snapshot_id
        """,
        (digest, DEMO_SOURCE_CONTRACT_VERSION),
    )
    return cur.fetchone()[0]


def _ensure_demo_source_counts(cur, snapshot_id) -> None:
    """Insert demo counts only when the snapshot still has none.

    ``enforce_analysis_source_count_freeze`` runs BEFORE INSERT. After
    the first run points at the snapshot, a later ``INSERT ... ON
    CONFLICT DO NOTHING`` still raises ``analysis_source_count_frozen_after_run``
    and rolls back the whole ``seed()`` transaction. Skip when counts
    already exist so ``make seed`` can be re-run.
    """
    cur.execute(
        "select 1 from analysis_source_count "
        "where analysis_source_snapshot_id = %s limit 1",
        (snapshot_id,),
    )
    if cur.fetchone() is not None:
        return
    cur.execute(
        """
        insert into analysis_source_count
            (analysis_source_snapshot_id, count_type_code, count_value)
        values
            (%s, 'analysis_count_document', 3),
            (%s, 'analysis_count_thread', 1),
            (%s, 'analysis_count_lineage_node', 5),
            (%s, 'analysis_count_lineage_edge', 4)
        """,
        (snapshot_id, snapshot_id, snapshot_id, snapshot_id),
    )


def _ensure_demo_source_snapshot_members(cur, snapshot_id, corporate_entity_id) -> None:
    """Freeze Demo Corp post ids on the shared snapshot when the table exists."""
    cur.execute(
        "select 1 from information_schema.tables "
        "where table_schema = 'public' "
        "and table_name = 'analysis_source_snapshot_member'"
    )
    if cur.fetchone() is None:
        return
    cur.execute(
        "select 1 from analysis_source_snapshot_member "
        "where analysis_source_snapshot_id = %s limit 1",
        (snapshot_id,),
    )
    if cur.fetchone() is not None:
        return
    cur.execute(
        """
        insert into analysis_source_snapshot_member
            (analysis_source_snapshot_id, source_post_id)
        select %s, post_id from source_post
        where corporate_entity_id = %s
          and created_at <= '2026-01-12T00:00:00Z'
        on conflict do nothing
        """,
        (snapshot_id, corporate_entity_id),
    )


def _seed_demo_analysis_run(cur, requested_by_account_id, corporate_entity_id) -> None:
    """Insert one Demo-Corp lineage run so Analysis runs is not empty.

    Aggregates only: three synthetic documents, one thread. Reuses the
    shared Demo Corp snapshot so a later TEPP run can attach to the
    same capture.
    """
    snapshot_id = _ensure_demo_source_snapshot(cur)
    _ensure_demo_source_counts(cur, snapshot_id)
    _ensure_demo_source_snapshot_members(cur, snapshot_id, corporate_entity_id)
    cur.execute(
        """
        select analysis_run_id from analysis_run
        where requested_by_account_id = %s
          and idempotency_key = %s
        """,
        (requested_by_account_id, DEMO_LINEAGE_IDEMPOTENCY_KEY),
    )
    run_row = cur.fetchone()
    if run_row is None:
        cur.execute(
            """
            insert into analysis_run
                (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                 requested_by_account_id, knowledge_cutoff,
                 configuration_schema_version, configuration_sha256,
                 code_revision_sha, requested_at)
            values (%s, 'analysis_run_lineage', %s,
                    %s, '2026-01-12T12:00:00Z', 'lineage-run-v1', %s, %s,
                    '2026-01-12T12:30:00Z')
            returning analysis_run_id
            """,
            (
                snapshot_id,
                DEMO_LINEAGE_IDEMPOTENCY_KEY,
                requested_by_account_id,
                "b" * 64,
                "c" * 40,
            ),
        )
        run_id = cur.fetchone()[0]
    else:
        run_id = run_row[0]
    cur.execute(
        """
        insert into analysis_run_scope
            (analysis_run_id, scope_kind_code, corporate_entity_id)
        values (%s, 'analysis_scope_corporate_entity', %s)
        on conflict (analysis_run_id) do nothing
        """,
        (run_id, corporate_entity_id),
    )
    cur.execute(
        "select 1 from analysis_run_status_event where analysis_run_id = %s limit 1",
        (run_id,),
    )
    if cur.fetchone() is None:
        for ordinal, status, occurred in (
            (1, "analysis_status_pending", "2026-01-12T12:31:00Z"),
            (2, "analysis_status_running", "2026-01-12T12:32:00Z"),
            (3, "analysis_status_succeeded", "2026-01-12T12:33:00Z"),
        ):
            cur.execute(
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at)
                values (%s, %s, %s, %s)
                """,
                (run_id, ordinal, status, occurred),
            )
    _seed_demo_run_reconstruction(cur, run_id, corporate_entity_id)
    _seed_demo_run_outbox(cur, run_id)


def seed_reconstruction_edges(rows: list[dict], weights: dict[str, float]) -> tuple:
    """ThreadWeave parent choices and digest for seed and start. Never a theta.

    ``weights`` is required (ADR 0200 point 1): the seed passes its
    fast-mlsirm demo-design estimate; unit tests inject synthetic
    weights.
    """
    from backend.app.analysis_run_start import reconstruction_result_digest
    from backend.app.lineage_ingestion import records_from_source_posts
    from lineageweave.lineage_persistence import lineage_edge_specs

    edges = lineage_edge_specs(records_from_source_posts(rows), weights=weights)
    return edges, reconstruction_result_digest(edges)


def _seed_demo_run_reconstruction(cur, analysis_run_id, corporate_entity_id) -> None:
    """Persist the designed A-100 fork on the seeded Succeeded lineage run.

    Seed already stamps Succeeded. Without run-scoped edges the home
    detail has cutoff titles and no fork. Reuses the same ThreadWeave
    path start uses. Does not invent a TEPP score.
    """
    from datetime import datetime, timezone

    cur.execute(
        "select 1 from analysis_run_reconstruction where analysis_run_id = %s",
        (analysis_run_id,),
    )
    if cur.fetchone() is not None:
        return
    cur.execute(
        """
        select post_id, post_title, created_at, visibility_code,
               corporate_entity_id, process_unit_id,
               thread_group_key, secondary_grouping_key
        from source_post
        where corporate_entity_id = %s
          and created_at <= %s
        order by created_at, post_title
        """,
        (corporate_entity_id, datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)),
    )
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    if not rows:
        return
    edges, digest = seed_reconstruction_edges(
        rows, demo_channel_weight_estimate().weights
    )
    finished = datetime(2026, 1, 12, 12, 33, tzinfo=timezone.utc)
    cur.execute(
        """
        insert into analysis_run_reconstruction
            (analysis_run_id, result_sha256, edge_count, reconstructed_at)
        values (%s, %s, %s, %s)
        on conflict do nothing
        """,
        (analysis_run_id, digest, len(edges), finished),
    )
    for edge in edges:
        cur.execute(
            """
            insert into analysis_run_lineage_edge
                (analysis_run_id, child_post_id, parent_post_id,
                 fused_score, reconstructed_at)
            values (%s, %s, %s, %s, %s)
            on conflict do nothing
            """,
            (analysis_run_id, edge.child_id, edge.parent_id, edge.fused_score, finished),
        )


def tepp_seed_request() -> AnalysisRunRequest:
    """Build the Demo Corp TEPP request against the shared snapshot digest."""
    return AnalysisRunRequest(
        idempotency_key=DEMO_TEPP_IDEMPOTENCY_KEY,
        tenant_workspace_id="demo-workspace",
        snapshot_id=demo_source_snapshot_sha256(),
        knowledge_cutoff="2026-01-12T12:00:00Z",
        model_contract_version="tepp-analysis-run-v1",
        output_profile="calibrated_event_measurement",
    )


def tepp_seed_outcome(client: TeppClient | None = None) -> tuple[str, str | None]:
    """Ask TEPP through the published client. A missing transport is Failed.

    Never invents a psychometric score. ``tepp_not_available`` means the
    channel was dropped, not a calibrated negative result. A strict
    accepted v1 envelope is transport evidence (ADR 0219), not a
    measurement. An invalid or unpublished envelope stays
    ``tepp_result_not_persisted`` and is not Succeeded.
    """
    from backend.app.analysis_run_start import _tepp_submission

    status, failure, _envelope = _tepp_submission(
        client or TeppClient(), tepp_seed_request()
    )
    return status, failure or None


def tepp_accepted_seed_request() -> AnalysisRunRequest:
    """Build the Demo Corp TEPP request whose seed transport accepts v1."""
    request = tepp_seed_request()
    return AnalysisRunRequest(
        idempotency_key=DEMO_TEPP_ACCEPTED_IDEMPOTENCY_KEY,
        tenant_workspace_id=request.tenant_workspace_id,
        snapshot_id=request.snapshot_id,
        knowledge_cutoff=request.knowledge_cutoff,
        model_contract_version=request.model_contract_version,
        output_profile=request.output_profile,
    )


def tepp_accepted_seed_client() -> TeppClient:
    """Return a fixture transport that yields TEPP's strict accepted v1 shape."""

    def _transport(payload: dict) -> dict:
        return {
            "contract_version": 1,
            "run_id": DEMO_TEPP_ACCEPTED_REMOTE_RUN_ID,
            "run_state": "accepted",
            "idempotency_key": payload["idempotency_key"],
        }

    return TeppClient(transport=_transport)


def tepp_accepted_seed_outcome(
    client: TeppClient | None = None,
) -> tuple[str, str | None, dict | None]:
    """Classify the accepted-fixture envelope without inventing a theta."""
    from backend.app.analysis_run_start import _tepp_submission

    status, failure, envelope = _tepp_submission(
        client or tepp_accepted_seed_client(), tepp_accepted_seed_request()
    )
    return status, failure or None, envelope


def _seed_demo_tepp_run(cur, requested_by_account_id, corporate_entity_id) -> None:
    """Insert one Demo-Corp TEPP run so the kind is visible without a live TEPP.

    Uses :func:`tepp_seed_outcome` against the shared lineage snapshot.
    Default transport is unavailable, so the run ends Failed /
    ``tepp_not_available`` -- never a fake theta.
    """
    snapshot_id = _ensure_demo_source_snapshot(cur)
    _ensure_demo_source_counts(cur, snapshot_id)
    _ensure_demo_source_snapshot_members(cur, snapshot_id, corporate_entity_id)
    cur.execute(
        """
        select analysis_run_id from analysis_run
        where requested_by_account_id = %s
          and idempotency_key = %s
        """,
        (requested_by_account_id, DEMO_TEPP_IDEMPOTENCY_KEY),
    )
    run_row = cur.fetchone()
    if run_row is None:
        cur.execute(
            """
            insert into analysis_run
                (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                 requested_by_account_id, knowledge_cutoff,
                 configuration_schema_version, configuration_sha256,
                 code_revision_sha, requested_at)
            values (%s, 'analysis_run_tepp', %s,
                    %s, '2026-01-12T12:00:00Z', 'tepp-run-v1', %s, %s,
                    '2026-01-12T12:34:00Z')
            returning analysis_run_id
            """,
            (
                snapshot_id,
                DEMO_TEPP_IDEMPOTENCY_KEY,
                requested_by_account_id,
                "d" * 64,
                "e" * 40,
            ),
        )
        run_id = cur.fetchone()[0]
    else:
        run_id = run_row[0]
    cur.execute(
        """
        insert into analysis_run_scope
            (analysis_run_id, scope_kind_code, corporate_entity_id)
        values (%s, 'analysis_scope_corporate_entity', %s)
        on conflict (analysis_run_id) do nothing
        """,
        (run_id, corporate_entity_id),
    )
    final_status, failure_code = tepp_seed_outcome()
    events = [
        (1, "analysis_status_pending", "2026-01-12T12:35:00Z", None),
        (2, "analysis_status_running", "2026-01-12T12:36:00Z", None),
        (3, final_status, "2026-01-12T12:37:00Z", failure_code),
    ]
    cur.execute(
        "select 1 from analysis_run_status_event where analysis_run_id = %s limit 1",
        (run_id,),
    )
    if cur.fetchone() is None:
        for ordinal, status, occurred, fail in events:
            cur.execute(
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at, failure_code)
                values (%s, %s, %s, %s, %s)
                """,
                (run_id, ordinal, status, occurred, fail),
            )
    _seed_demo_run_outbox(cur, run_id)


def _seed_tepp_accepted_receipt(cur, analysis_run_id, request, envelope) -> None:
    """Persist TEPP acceptance as transport evidence, never a measurement."""
    remote_run_id = envelope.get("run_id")
    if envelope.get("run_state") != "accepted" or not isinstance(remote_run_id, str):
        return
    request_json = json.dumps(request.to_json(), separators=(",", ":"), sort_keys=True)
    receipt_json = json.dumps(envelope, separators=(",", ":"), sort_keys=True)
    cur.execute(
        """
        insert into analysis_run_tepp_receipt
            (analysis_run_id, remote_run_id, request_sha256, receipt_sha256,
             accepted_status_code, received_at)
        values (%s, %s, %s, %s, 'accepted', '2026-01-12T12:36:00Z')
        on conflict do nothing
        """,
        (
            analysis_run_id,
            remote_run_id,
            hashlib.sha256(request_json.encode()).hexdigest(),
            hashlib.sha256(receipt_json.encode()).hexdigest(),
        ),
    )


def _seed_demo_tepp_accepted_run(cur, requested_by_account_id, corporate_entity_id) -> None:
    """Insert one Demo-Corp TEPP run that stays Running after accepted v1.

    Uses :func:`tepp_accepted_seed_client` so ``make seed`` can show the
    buyer receipt copy. Missing-transport Failed remains the other TEPP
    fixture. Never invents a theta or a completed result.
    """
    snapshot_id = _ensure_demo_source_snapshot(cur)
    _ensure_demo_source_counts(cur, snapshot_id)
    _ensure_demo_source_snapshot_members(cur, snapshot_id, corporate_entity_id)
    cur.execute(
        """
        select analysis_run_id from analysis_run
        where requested_by_account_id = %s
          and idempotency_key = %s
        """,
        (requested_by_account_id, DEMO_TEPP_ACCEPTED_IDEMPOTENCY_KEY),
    )
    run_row = cur.fetchone()
    if run_row is None:
        cur.execute(
            """
            insert into analysis_run
                (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                 requested_by_account_id, knowledge_cutoff,
                 configuration_schema_version, configuration_sha256,
                 code_revision_sha, requested_at)
            values (%s, 'analysis_run_tepp', %s,
                    %s, '2026-01-12T12:00:00Z', 'tepp-run-v1', %s, %s,
                    '2026-01-12T12:34:00Z')
            returning analysis_run_id
            """,
            (
                snapshot_id,
                DEMO_TEPP_ACCEPTED_IDEMPOTENCY_KEY,
                requested_by_account_id,
                "d" * 64,
                "e" * 40,
            ),
        )
        run_id = cur.fetchone()[0]
    else:
        run_id = run_row[0]
    cur.execute(
        """
        insert into analysis_run_scope
            (analysis_run_id, scope_kind_code, corporate_entity_id)
        values (%s, 'analysis_scope_corporate_entity', %s)
        on conflict (analysis_run_id) do nothing
        """,
        (run_id, corporate_entity_id),
    )
    status, failure, envelope = tepp_accepted_seed_outcome()
    persist_receipt = (
        status == "analysis_status_running"
        and envelope is not None
        and envelope.get("run_state") == "accepted"
    )
    if persist_receipt:
        _seed_tepp_accepted_receipt(cur, run_id, tepp_accepted_seed_request(), envelope)
        events = [
            (1, "analysis_status_pending", "2026-01-12T12:35:00Z", None),
            (2, "analysis_status_running", "2026-01-12T12:36:00Z", None),
        ]
    else:
        events = [
            (1, "analysis_status_pending", "2026-01-12T12:35:00Z", None),
            (2, "analysis_status_running", "2026-01-12T12:36:00Z", None),
            (3, status, "2026-01-12T12:37:00Z", failure),
        ]
    cur.execute(
        "select 1 from analysis_run_status_event where analysis_run_id = %s limit 1",
        (run_id,),
    )
    if cur.fetchone() is None:
        for ordinal, event_status, occurred, fail in events:
            cur.execute(
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at, failure_code)
                values (%s, %s, %s, %s, %s)
                """,
                (run_id, ordinal, event_status, occurred, fail),
            )
    _seed_demo_run_outbox(cur, run_id, delivered=not persist_receipt)


def topic_lineage_seed_request() -> AnalysisRunRequest:
    """Build the Demo Corp topic-lineage request against the shared snapshot digest.

    Same wire shape as :func:`tepp_seed_request` (ADR 0132) -- only the
    model contract and output profile select TRSL-TM topic identity plus
    CHRONOS/TDT event-intelligence status instead of calibrated
    psychometric measurement.
    """
    return AnalysisRunRequest(
        idempotency_key=DEMO_TOPIC_LINEAGE_IDEMPOTENCY_KEY,
        tenant_workspace_id="demo-workspace",
        snapshot_id=demo_source_snapshot_sha256(),
        knowledge_cutoff="2026-01-12T12:00:00Z",
        model_contract_version="tepp-topic-lineage-v1",
        output_profile="topic_identity_lineage",
    )


def topic_lineage_seed_outcome(client: TeppClient | None = None) -> tuple[str, str | None]:
    """Ask TEPP through the published client. A missing transport is Failed.

    Never invents a topic identity or CHRONOS/TDT event prediction.
    ``tepp_not_available`` means the channel was dropped, not an abstained
    measurement. A live envelope is also not yet a persistable result in
    this seed, so the run is not stamped Succeeded.
    """
    request = topic_lineage_seed_request()
    try:
        (client or TeppClient()).submit_analysis_run(request)
    except TeppNotAvailable:
        return "analysis_status_failed", "tepp_not_available"
    return "analysis_status_failed", "tepp_result_not_persisted"


def _seed_demo_topic_lineage_run(cur, requested_by_account_id, corporate_entity_id) -> None:
    """Insert one Demo-Corp topic-lineage run so the kind is visible without a live TEPP.

    Mirrors :func:`_seed_demo_tepp_run` (ADR 0132). Default transport is
    unavailable, so the run ends Failed / ``tepp_not_available`` -- never
    a fabricated topic model.
    """
    snapshot_id = _ensure_demo_source_snapshot(cur)
    _ensure_demo_source_counts(cur, snapshot_id)
    _ensure_demo_source_snapshot_members(cur, snapshot_id, corporate_entity_id)
    cur.execute(
        """
        select analysis_run_id from analysis_run
        where requested_by_account_id = %s
          and idempotency_key = %s
        """,
        (requested_by_account_id, DEMO_TOPIC_LINEAGE_IDEMPOTENCY_KEY),
    )
    run_row = cur.fetchone()
    if run_row is None:
        cur.execute(
            """
            insert into analysis_run
                (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                 requested_by_account_id, knowledge_cutoff,
                 configuration_schema_version, configuration_sha256,
                 code_revision_sha, requested_at)
            values (%s, 'analysis_run_topic_lineage', %s,
                    %s, '2026-01-12T12:00:00Z', 'topic-lineage-run-v1', %s, %s,
                    '2026-01-12T12:34:00Z')
            returning analysis_run_id
            """,
            (
                snapshot_id,
                DEMO_TOPIC_LINEAGE_IDEMPOTENCY_KEY,
                requested_by_account_id,
                "d" * 64,
                "e" * 40,
            ),
        )
        run_id = cur.fetchone()[0]
    else:
        run_id = run_row[0]
    cur.execute(
        """
        insert into analysis_run_scope
            (analysis_run_id, scope_kind_code, corporate_entity_id)
        values (%s, 'analysis_scope_corporate_entity', %s)
        on conflict (analysis_run_id) do nothing
        """,
        (run_id, corporate_entity_id),
    )
    final_status, failure_code = topic_lineage_seed_outcome()
    events = [
        (1, "analysis_status_pending", "2026-01-12T12:35:00Z", None),
        (2, "analysis_status_running", "2026-01-12T12:36:00Z", None),
        (3, final_status, "2026-01-12T12:37:00Z", failure_code),
    ]
    cur.execute(
        "select 1 from analysis_run_status_event where analysis_run_id = %s limit 1",
        (run_id,),
    )
    if cur.fetchone() is None:
        for ordinal, status, occurred, fail in events:
            cur.execute(
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at, failure_code)
                values (%s, %s, %s, %s, %s)
                """,
                (run_id, ordinal, status, occurred, fail),
            )
    _seed_demo_run_outbox(cur, run_id)


def _seed_demo_report_run(cur, requested_by_account_id, corporate_entity_id) -> None:
    """Record the already-built Demo Corp period report on the shared snapshot.

    ``_seed_demo_period_report`` persists calibrated report tables first.
    This registry row is Succeeded because that write already happened.
    It does not copy a theta onto ``analysis_run``, does not invent a
    local psychometric substitute, and does not enqueue start outbox
    work (ADR 0024). Start stays 422.
    """
    snapshot_id = _ensure_demo_source_snapshot(cur)
    _ensure_demo_source_counts(cur, snapshot_id)
    _ensure_demo_source_snapshot_members(cur, snapshot_id, corporate_entity_id)
    cur.execute(
        """
        select analysis_run_id from analysis_run
        where requested_by_account_id = %s
          and idempotency_key = %s
        """,
        (requested_by_account_id, DEMO_REPORT_IDEMPOTENCY_KEY),
    )
    run_row = cur.fetchone()
    if run_row is None:
        cur.execute(
            """
            insert into analysis_run
                (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                 requested_by_account_id, knowledge_cutoff,
                 configuration_schema_version, configuration_sha256,
                 code_revision_sha, requested_at)
            values (%s, 'analysis_run_report', %s,
                    %s, '2026-01-12T12:00:00Z', 'report-run-v1', %s, %s,
                    '2026-01-12T12:38:00Z')
            returning analysis_run_id
            """,
            (
                snapshot_id,
                DEMO_REPORT_IDEMPOTENCY_KEY,
                requested_by_account_id,
                "f" * 64,
                "a" * 40,
            ),
        )
        run_id = cur.fetchone()[0]
    else:
        run_id = run_row[0]
    cur.execute(
        """
        insert into analysis_run_scope
            (analysis_run_id, scope_kind_code, corporate_entity_id)
        values (%s, 'analysis_scope_corporate_entity', %s)
        on conflict (analysis_run_id) do nothing
        """,
        (run_id, corporate_entity_id),
    )
    cur.execute(
        "select 1 from analysis_run_status_event where analysis_run_id = %s limit 1",
        (run_id,),
    )
    if cur.fetchone() is None:
        for ordinal, status, occurred in (
            (1, "analysis_status_pending", "2026-01-12T12:39:00Z"),
            (2, "analysis_status_running", "2026-01-12T12:40:00Z"),
            (3, "analysis_status_succeeded", "2026-01-12T12:41:00Z"),
        ):
            cur.execute(
                """
                insert into analysis_run_status_event
                    (analysis_run_id, status_ordinal, status_code, occurred_at)
                values (%s, %s, %s, %s)
                """,
                (run_id, ordinal, status, occurred),
            )


def _seed_demo_run_outbox(cur, analysis_run_id, *, delivered: bool = True) -> None:
    """Record the start-work outbox path used by live start.

    A terminal seed run is claimed then delivered. A Running TEPP
    accepted-receipt seed stays claimed so a later status read can
    resume without resubmitting (ADR 0219). No theta is stored.
    """
    from datetime import datetime, timezone

    from backend.app.analysis_run_outbox import outbox_request_digest

    cur.execute(
        "select 1 from analysis_run_outbox where analysis_run_id = %s",
        (analysis_run_id,),
    )
    if cur.fetchone() is not None:
        return
    cur.execute(
        """
        select run.run_kind_code, run.knowledge_cutoff, snapshot.snapshot_sha256
        from analysis_run run
        join analysis_source_snapshot snapshot
          on snapshot.analysis_source_snapshot_id = run.analysis_source_snapshot_id
        where run.analysis_run_id = %s
        """,
        (analysis_run_id,),
    )
    row = cur.fetchone()
    if row is None:
        return
    work_kind_code, knowledge_cutoff, snapshot_sha256 = row
    digest = outbox_request_digest(
        analysis_run_id=str(analysis_run_id),
        work_kind_code=work_kind_code,
        snapshot_sha256=snapshot_sha256,
        knowledge_cutoff=knowledge_cutoff,
    )
    if work_kind_code in ("analysis_run_tepp", "analysis_run_topic_lineage"):
        claimed = datetime(2026, 1, 12, 12, 36, tzinfo=timezone.utc)
        delivered_at = datetime(2026, 1, 12, 12, 37, tzinfo=timezone.utc)
    else:
        claimed = datetime(2026, 1, 12, 12, 32, tzinfo=timezone.utc)
        delivered_at = datetime(2026, 1, 12, 12, 33, tzinfo=timezone.utc)
    cur.execute(
        """
        insert into analysis_run_outbox
            (analysis_run_id, work_kind_code, request_sha256, enqueued_at)
        values (%s, %s, %s, %s)
        on conflict do nothing
        """,
        (analysis_run_id, work_kind_code, digest, claimed),
    )
    deliveries = [(1, "analysis_outbox_claimed", claimed)]
    if delivered:
        deliveries.append((2, "analysis_outbox_delivered", delivered_at))
    for ordinal, status, occurred in deliveries:
        cur.execute(
            """
            insert into analysis_run_outbox_delivery
                (analysis_run_id, delivery_ordinal, delivery_status_code, occurred_at)
            values (%s, %s, %s, %s)
            on conflict do nothing
            """,
            (analysis_run_id, ordinal, status, occurred),
        )


DEFAULT_BACKEND_BASE_URL = "http://localhost:18420"


def _warm_seeded_post_content(
    postgres_dsn: str, keycloak_base_url: str, backend_base_url: str
) -> None:
    """Open each seeded post once through the API to start content ingestion.

    Post-content extraction (units, embeddings, embedded images) is
    enqueued lazily when a post detail is first served. Seeded posts are
    inserted straight into Postgres, so until someone opens them the
    pipeline stays empty and image citation has nothing to cite. This
    replays the exact production path with the demo reader account
    instead of duplicating the enqueue SQL here.
    """
    for _ in range(60):
        try:
            get_json(f"{backend_base_url}/healthz", timeout=5.0)
            break
        except Exception:
            time.sleep(2)
    else:
        raise RuntimeError(
            f"backend at {backend_base_url} is not serving /healthz; run `make up` first"
        )
    token = post_form(
        f"{keycloak_base_url}/realms/lineageweave-demo/protocol/openid-connect/token",
        {
            "client_id": "lineageweave-frontend",
            "grant_type": "password",
            "username": "demo.analyst",
            "password": "lineageweave-demo-only",
        },
        timeout=30.0,
    )["access_token"]
    connection = psycopg2.connect(postgres_dsn)
    try:
        with connection.cursor() as cur:
            cur.execute(
                "select post_id from source_post where post_title like 'Demo %post'"
            )
            post_ids = [str(row[0]) for row in cur.fetchall()]
    finally:
        # psycopg2's context manager only manages the transaction; close
        # explicitly so no idle connection outlives the HTTP warm-up.
        connection.close()
    for post_id in post_ids:
        get_json(
            f"{backend_base_url}/api/posts/{post_id}/content",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60.0,
        )
    print(f"Warmed post-content ingestion for {len(post_ids)} seeded posts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-dsn", default=DEFAULT_POSTGRES_DSN)
    parser.add_argument("--keycloak-base-url", default=DEFAULT_KEYCLOAK_BASE_URL)
    parser.add_argument("--keycloak-admin-user", default=DEFAULT_KEYCLOAK_ADMIN_USER)
    parser.add_argument(
        "--keycloak-admin-password",
        default=os.environ.get("KEYCLOAK_ADMIN_PASSWORD"),
        help="Keycloak master admin password (or KEYCLOAK_ADMIN_PASSWORD). Required.",
    )
    parser.add_argument("--valkey-url", default=DEFAULT_VALKEY_URL)
    parser.add_argument("--backend-base-url", default=DEFAULT_BACKEND_BASE_URL)
    args = parser.parse_args()
    if not args.keycloak_admin_password:
        parser.error("set KEYCLOAK_ADMIN_PASSWORD or pass --keycloak-admin-password")

    subjects = _fetch_demo_user_subjects(args.keycloak_base_url, args.keycloak_admin_user, args.keycloak_admin_password)
    seed(args.postgres_dsn, subjects, args.valkey_url)
    _warm_seeded_post_content(args.postgres_dsn, args.keycloak_base_url, args.backend_base_url)
    print(f"Seeded synthetic demo data for accounts: {subjects}")


if __name__ == "__main__":
    main()
