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

Usage: python3 scripts/seed_demo_data.py [--postgres-dsn ...] [--keycloak-base-url ...]
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request

import psycopg2

REALM = "lineageweave-demo"
DEFAULT_POSTGRES_DSN = "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
DEFAULT_KEYCLOAK_BASE_URL = "http://localhost:18080"
DEFAULT_KEYCLOAK_ADMIN_USER = "admin"
DEFAULT_KEYCLOAK_ADMIN_PASSWORD = "admin_dev_only"  # nosec B105 -- throwaway local-dev-only Keycloak seed credential


def _post_form(url: str, fields: dict[str, str]) -> dict:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 -- local dev Keycloak, http by design
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, bearer_token: str) -> list[dict]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {bearer_token}"})
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _fetch_demo_user_subjects(base_url: str, admin_user: str, admin_password: str) -> dict[str, str]:
    admin_token = _post_form(
        f"{base_url}/realms/master/protocol/openid-connect/token",
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": admin_user,
            "password": admin_password,
        },
    )["access_token"]

    subjects: dict[str, str] = {}
    for username in ("demo.analyst", "demo.admin"):
        query = urllib.parse.urlencode({"username": username, "exact": "true"})
        users = _get_json(f"{base_url}/admin/realms/{REALM}/users?{query}", admin_token)
        if not users:
            raise SystemExit(f"Keycloak user '{username}' not found in realm '{REALM}' -- did the realm import run?")
        subjects[username] = users[0]["id"]
    return subjects


def seed(postgres_dsn: str, subjects: dict[str, str]) -> None:
    conn = psycopg2.connect(postgres_dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into common_lookup_value (lookup_category, lookup_code, lookup_label, display_order) values
                    ('corporate_entity_level', 'group', 'Group', 0),
                    ('corporate_entity_level', 'company', 'Company', 1),
                    ('post_visibility', 'public', 'Public', 0),
                    ('post_visibility', 'private', 'Private', 1),
                    ('voc_type', 'voc', 'Voice of Customer', 0),
                    ('voc_type', 'vom', 'Voice of Market', 1),
                    ('permission', 'post_read', 'Read posts', 0),
                    ('permission', 'post_admin', 'Administer posts', 1)
                on conflict (lookup_code) do nothing
                """
            )

            cur.execute(
                "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
                "values ('DEMO-CORP-01', 'Demo Corp', 'group') "
                "on conflict (corporate_entity_code) do update set entity_name = excluded.entity_name "
                "returning corporate_entity_id"
            )
            corporate_entity_id = cur.fetchone()[0]

            cur.execute(
                "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) values "
                "(%s, 'DEMO-PU-A', 'Demo Sales Unit A'), (%s, 'DEMO-PU-HQ', 'Demo Headquarters') "
                "on conflict (process_unit_code) do update set process_unit_name = excluded.process_unit_name "
                "returning process_unit_code, process_unit_id",
                (corporate_entity_id, corporate_entity_id),
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

            cur.execute("select post_id from post where post_title = 'Demo public post'")
            if cur.fetchone() is None:
                cur.execute(
                    "insert into post (author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, voc_type_code, visibility_code) "
                    "values (%s, %s, %s, 'Demo public post', 'A synthetic public post visible to every demo account.', 'voc', 'public')",
                    (account_ids["demo.analyst"], corporate_entity_id, process_units["DEMO-PU-A"]),
                )
                cur.execute(
                    "insert into post (author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, voc_type_code, visibility_code) "
                    "values (%s, %s, %s, 'Demo private post', 'A synthetic private post scoped to Demo Corp accounts.', 'vom', 'private')",
                    (account_ids["demo.admin"], corporate_entity_id, process_units["DEMO-PU-HQ"]),
                )

        conn.commit()
    finally:
        conn.close()


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
