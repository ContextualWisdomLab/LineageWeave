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
            grouping_sql = Path(__file__).resolve().parents[1] / "migrations" / "0002_thread_grouping_keys.sql"
            cur.execute(grouping_sql.read_text())
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
