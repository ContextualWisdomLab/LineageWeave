#!/usr/bin/env python3
"""Seeds synthetic Phase 1 demo data into the running Postgres/Keycloak
stack, so the whole login -> post-list -> post-detail path is demonstrable
end to end (per ADR 0001: real infrastructure, synthetic content only).

Genuinely real, not fabricated locally and hoped to match: this script logs
into Keycloak's own admin REST API to fetch the actual `sub` (user id) of
the two demo accounts seeded by docker/keycloak/realm-export.json, then
inserts user_account rows in Postgres keyed by those real subject ids --
the same identity Keycloak issues in an access token's `sub` claim, which
is exactly what backend.app.auth looks up.

HTTP goes through ``lineageweave.http_client`` (http(s) allowlist).

Usage: python3 scripts/seed_demo_data.py [--postgres-dsn ...] [--keycloak-base-url ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlencode

# Allow `python3 scripts/seed_demo_data.py` from a checkout without install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2

from lineageweave.http_client import get_json_list, post_form

REALM = "lineageweave-demo"
DEFAULT_POSTGRES_DSN = "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
DEFAULT_KEYCLOAK_BASE_URL = "http://localhost:18080"
DEFAULT_KEYCLOAK_ADMIN_USER = "admin"
DEFAULT_KEYCLOAK_ADMIN_PASSWORD = "admin_dev_only"  # nosec B105 -- throwaway local-dev-only Keycloak seed credential


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
        )
        if not users:
            raise SystemExit(f"Keycloak user '{username}' not found in realm '{REALM}' -- did the realm import run?")
        subjects[username] = users[0]["id"]
    return subjects


def seed(postgres_dsn: str, subjects: dict[str, str]) -> None:
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
            cur.execute(
                """
                insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
                    ('corporate_entity_level', 'group', 'Group', 0),
                    ('corporate_entity_level', 'company', 'Company', 1),
                    ('corporate_entity_level', 'plant', 'Plant', 2),
                    ('post_visibility', 'public', 'Public', 0),
                    ('post_visibility', 'private', 'Private', 1),
                    ('voc_type', 'voc', 'Voice of Customer', 0),
                    ('voc_type', 'vom', 'Voice of Market', 1),
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
                    ('ticket_status', 'closed', 'Closed', 2)
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

            cur.execute("select post_id from source_post where post_title = 'Demo public post'")
            if cur.fetchone() is None:
                cur.execute(
                    "insert into source_post (author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, voc_type_code, visibility_code) "
                    "values (%s, %s, %s, 'Demo public post', "
                    "'Ada West at Demo Corp followed up with Priya Nair at Northridge Grid about the delayed shipment.', "
                    "'voc', 'public')",
                    (account_ids["demo.analyst"], corporate_entity_id, process_units["DEMO-PU-A"]),
                )
                cur.execute(
                    "insert into source_post (author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, voc_type_code, visibility_code) "
                    "values (%s, %s, %s, 'Demo private post', 'A synthetic private post scoped to Demo Corp accounts.', 'vom', 'private')",
                    (account_ids["demo.admin"], corporate_entity_id, process_units["DEMO-PU-HQ"]),
                )

            cur.execute("select post_id from source_post where post_title = 'Demo public post'")
            demo_public_post_id = cur.fetchone()[0]
            cur.execute(
                "update source_post set post_body = %s where post_id = %s",
                (
                    "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid about the delayed shipment.",
                    demo_public_post_id,
                ),
            )
            cur.execute(
                "insert into post_counterparty_entity (post_id, counterparty_entity_name, relationship_type_code) "
                "values (%s, 'Northridge Grid', 'rel_voc') on conflict do nothing",
                (demo_public_post_id,),
            )
            _seed_demo_public_summary(cur, demo_public_post_id)
            cur.execute("select person_id from cataloged_person where person_name = 'Ada West'")
            if cur.fetchone() is None:
                from lineageweave.knowledge_graph import knowledge_graph_edges_for_post

                cur.execute(
                    "insert into cataloged_person (person_name, person_side_code) values "
                    "('Ada West', 'our_side'), ('Priya Nair', 'counterparty') "
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
            _seed_demo_period_report(
                cur,
                account_ids["demo.analyst"],
                corporate_entity_id,
                process_units["DEMO-PU-LINEAGE"],
            )

        conn.commit()
    finally:
        conn.close()


def insert_fixture_source_posts(cur, author_account_id, corporate_entity_id, process_unit_id):
    """Insert ``sample_records()`` as ``source_post`` rows seed and rebuild share.

    Writes ``thread_group_key``, ``secondary_grouping_key``, and
    ``created_at = occurred_at`` so a later ``POST /api/lineage/rebuild``
    sees the same grouping and timeline reconstruct() was designed on.
    Returns persisted ``Record``s whose ids are the new post UUIDs.
    """
    from lineageweave.fixtures import sample_records
    from lineageweave.models import Record

    persisted: list[Record] = []
    for rec in sample_records():
        voc_type = "voc" if rec.secondary_key else "vom"
        cur.execute(
            "insert into source_post "
            "(author_account_id, corporate_entity_id, process_unit_id, "
            " post_title, post_body, voc_type_code, visibility_code, "
            " thread_group_key, secondary_grouping_key, created_at) "
            "values (%s, %s, %s, %s, %s, %s, 'public', %s, %s, %s) returning post_id",
            (
                author_account_id,
                corporate_entity_id,
                process_unit_id,
                rec.label,
                rec.label,
                voc_type,
                rec.group_key,
                rec.secondary_key,
                rec.occurred_at,
            ),
        )
        post_id = str(cur.fetchone()[0])
        persisted.append(
            Record(post_id, rec.group_key, rec.label, rec.occurred_at, rec.secondary_key)
        )
    return persisted


def _seed_reconstructed_lineage(cur, author_account_id, corporate_entity_id, process_unit_id) -> None:
    """Persist fixtures.sample_records() as source_posts plus reconstruct edges.

    Without this, GET /api/posts/{id}/lineage is empty on a freshly seeded
    demo: the Event Lineage panel has nothing to show even though
    reconstruct() already knows the A-100 fork.
    """
    from lineageweave.fixtures import sample_records
    from lineageweave.lineage_persistence import lineage_edge_specs

    records = sample_records()
    cur.execute("select 1 from source_post where post_title = %s", (records[0].label,))
    if cur.fetchone() is not None:
        return

    persisted = insert_fixture_source_posts(
        cur, author_account_id, corporate_entity_id, process_unit_id
    )
    for edge in lineage_edge_specs(persisted):
        cur.execute(
            "insert into post_lineage_edge (parent_post_id, child_post_id, fused_score) "
            "values (%s, %s, %s) on conflict do nothing",
            (edge.parent_id, edge.child_id, edge.fused_score),
        )


def _seed_demo_public_summary(cur, post_id) -> None:
    """Write the popup summary for the demo public post.

    Idempotent: re-seed replaces the same row so GET /api/posts/{id}/summary
    stays non-empty without a live orchestrator.
    """
    from backend.app.post_summary_ingestion import seeded_demo_summary

    summary = seeded_demo_summary()
    cur.execute("delete from post_summary_result where post_id = %s", (post_id,))
    cur.execute(
        "insert into post_summary_result (post_id, korean_summary) values (%s, %s)",
        (post_id, summary.korean_summary),
    )
    for ordinal, event_text in enumerate(summary.key_events):
        cur.execute(
            "insert into post_summary_event (post_id, event_ordinal, event_text) values (%s, %s, %s)",
            (post_id, ordinal, event_text),
        )
    for role in summary.roles_and_responsibilities:
        cur.execute(
            "insert into post_summary_role (post_id, person_name, responsibility) values (%s, %s, %s)",
            (post_id, role.person_name, role.responsibility),
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
    from datetime import datetime, timezone

    from lineageweave.fixtures import ambiguous_commitment_post

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
                datetime(2026, 1, 5, tzinfo=timezone.utc),
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
            "Send Riverbend the revised delivery schedule.",
            "2026-01-09",
            "Send Riverbend the revised delivery schedule.",
        ),
    )


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


def _seed_demo_period_report(cur, author_account_id, corporate_entity_id, process_unit_id) -> None:
    """Insert two process units on one shared metric, plus a linked W03.

    High-band and low-band posts live in different process units. A
    pooled free-calibrate writes the shared bank; each unit is then
    FIPC-scored so the buyer can compare them. W03 is all-high on the
    high unit. Categories are constructed; thetas come only from
    ``score_groups_on_shared_metric``.
    """
    from datetime import datetime, timezone

    from lineageweave.period_report import score_groups_on_shared_metric
    from lineageweave.post_evaluation import IRT_CATEGORY_COUNT, RUBRIC_VERSION

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

    cur.execute(
        "select link_method from report_period_score "
        "where grouping_kind = 'process_unit' and grouping_key = %s "
        "and period_code = %s and rubric_version = %s",
        (high_key, w03, RUBRIC_VERSION),
    )
    existing = cur.fetchone()
    if existing is not None and existing[0] == "fipc":
        return

    bank_report, scored = score_groups_on_shared_metric(
        {
            high_key: (w02_high_ids, w02_high_cells),
            low_key: (w02_low_ids, w02_low_cells),
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
                w02_high_ids + w02_low_ids,
                w02_high_cells + w02_low_cells,
            )
        },
        item_bank=bank,
        source_period_code=w02,
    )
    for grouping_key, report in corp_scored.items():
        _persist_seed_period_report(cur, "corporate_entity", grouping_key, w02, report)
    _, thread_scored = score_groups_on_shared_metric(
        {
            "A-100": (w02_high_ids, w02_high_cells),
            "B-200": (w02_low_ids, w02_low_cells),
        },
        item_bank=bank,
        source_period_code=w02,
    )
    for grouping_key, report in thread_scored.items():
        _persist_seed_period_report(cur, "thread_group", grouping_key, w02, report)

    high_w02 = scored[high_key]
    _, week3 = score_groups_on_shared_metric(
        {high_key: (w03_ids, w03_cells)},
        item_bank=high_w02.item_bank,
        previous_means={high_key: high_w02.mean_theta},
        source_period_code=w03,
    )
    _persist_seed_period_report(cur, "process_unit", high_key, w03, week3[high_key])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-dsn", default=DEFAULT_POSTGRES_DSN)
    parser.add_argument("--keycloak-base-url", default=DEFAULT_KEYCLOAK_BASE_URL)
    parser.add_argument("--keycloak-admin-user", default=DEFAULT_KEYCLOAK_ADMIN_USER)
    parser.add_argument("--keycloak-admin-password", default=DEFAULT_KEYCLOAK_ADMIN_PASSWORD)
    args = parser.parse_args()

    subjects = _fetch_demo_user_subjects(args.keycloak_base_url, args.keycloak_admin_user, args.keycloak_admin_password)
    seed(args.postgres_dsn, subjects)
    print(f"Seeded synthetic demo data for accounts: {subjects}")


if __name__ == "__main__":
    main()
