#!/usr/bin/env python3
"""Provision DB-owned authorization for local confidential test clients.

The local Keycloak realm owns the deterministic service-account subjects. This
script only maps those already-declared subjects into LineageWeave's normalized
``user_account`` / affiliation / role model after ``seed_demo_data.py`` has
created the synthetic Demo Corp, process units, and access roles. It does not
call Keycloak and cannot mint tokens.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

import psycopg2


DEFAULT_POSTGRES_DSN = (
    "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
)
DEMO_CORPORATE_ENTITY_CODE = "DEMO-CORP-01"


@dataclass(frozen=True)
class LocalServiceAccount:
    """Normalized authorization target for one deterministic realm subject."""

    client_id: str
    subject_id: str
    display_name: str
    email_address: str
    process_unit_code: str
    role_code: str


LOCAL_SERVICE_ACCOUNTS = (
    LocalServiceAccount(
        client_id="lineageweave-test-automation",
        subject_id="33333333-3333-4333-8333-333333333333",
        display_name="LineageWeave Test Automation",
        email_address="lineageweave-test-automation@example.test",
        process_unit_code="DEMO-PU-A",
        role_code="viewer",
    ),
    LocalServiceAccount(
        client_id="lineageweave-test-admin",
        subject_id="44444444-4444-4444-8444-444444444444",
        display_name="LineageWeave Test Admin",
        email_address="lineageweave-test-admin@example.test",
        process_unit_code="DEMO-PU-HQ",
        role_code="admin",
    ),
)


def _one(cur, query: str, params: tuple[object, ...], label: str):
    """Return one prerequisite row or fail instead of fabricating local truth."""
    cur.execute(query, params)
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(
            f"missing {label}; run scripts/seed_demo_data.py before provisioning local service accounts"
        )
    return row[0]


def provision(postgres_dsn: str) -> None:
    """Upsert the two service actors with exact affiliation and role sets."""
    conn = psycopg2.connect(postgres_dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                corporate_entity_id = _one(
                    cur,
                    "select corporate_entity_id from corporate_entity where corporate_entity_code = %s",
                    (DEMO_CORPORATE_ENTITY_CODE,),
                    f"corporate entity {DEMO_CORPORATE_ENTITY_CODE}",
                )

                for account in LOCAL_SERVICE_ACCOUNTS:
                    process_unit_id = _one(
                        cur,
                        "select process_unit_id from process_unit "
                        "where corporate_entity_id = %s and process_unit_code = %s",
                        (corporate_entity_id, account.process_unit_code),
                        f"process unit {account.process_unit_code}",
                    )
                    role_id = _one(
                        cur,
                        "select access_role_id from access_role where role_code = %s",
                        (account.role_code,),
                        f"access role {account.role_code}",
                    )

                    cur.execute(
                        "insert into user_account "
                        "(external_subject_id, display_name, email_address) "
                        "values (%s, %s, %s) "
                        "on conflict (external_subject_id) do update set "
                        "display_name = excluded.display_name, "
                        "email_address = excluded.email_address "
                        "returning user_account_id",
                        (
                            account.subject_id,
                            account.display_name,
                            account.email_address,
                        ),
                    )
                    user_account_id = cur.fetchone()[0]

                    # These are deterministic local fixture actors. Replacing only
                    # their own mappings prevents a prior seed from accumulating a
                    # broader scope or role than the current contract allows.
                    cur.execute(
                        "delete from account_affiliation where user_account_id = %s",
                        (user_account_id,),
                    )
                    cur.execute(
                        "insert into account_affiliation "
                        "(user_account_id, corporate_entity_id, process_unit_id) "
                        "values (%s, %s, %s)",
                        (user_account_id, corporate_entity_id, process_unit_id),
                    )
                    cur.execute(
                        "delete from account_role_assignment where user_account_id = %s",
                        (user_account_id,),
                    )
                    cur.execute(
                        "insert into account_role_assignment "
                        "(user_account_id, access_role_id) values (%s, %s)",
                        (user_account_id, role_id),
                    )
    finally:
        conn.close()


def _parse_args() -> argparse.Namespace:
    """Parse the local Postgres target without accepting identity credentials."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--postgres-dsn",
        default=os.environ.get(
            "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", DEFAULT_POSTGRES_DSN
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Provision the deterministic local service actors."""
    args = _parse_args()
    provision(args.postgres_dsn)


if __name__ == "__main__":
    main()
