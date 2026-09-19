#!/usr/bin/env python3
"""Provision DB-owned authorization for local confidential test clients.

The local Keycloak realm owns the deterministic service-account subjects. This
script reads those subjects from the checked-in realm fixture and maps them into
LineageWeave's normalized ``user_account`` / affiliation / role model after
``seed_demo_data.py`` has created the synthetic Demo Corp, process units, and
access roles. It does not call Keycloak and cannot mint tokens.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

import psycopg2


DEFAULT_POSTGRES_DSN = (
    "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
)
DEFAULT_REALM_EXPORT_PATH = (
    Path(__file__).resolve().parents[1] / "docker" / "keycloak" / "realm-export.json"
)
DEMO_CORPORATE_ENTITY_CODE = "DEMO-CORP-01"
LINEAGEWEAVE_API_AUDIENCE = "lineageweave-api"
LINEAGEWEAVE_MCP_AUDIENCE = "http://localhost:18001/mcp"


@dataclass(frozen=True)
class LocalServiceAccount:
    """Normalized authorization target for one realm-owned service subject."""

    client_id: str
    subject_id: str
    display_name: str
    email_address: str
    process_unit_code: str
    role_code: str


@dataclass(frozen=True)
class LocalServiceAccountBinding:
    """LineageWeave authorization metadata keyed by an identity-owner client id."""

    client_id: str
    display_name: str
    email_address: str
    process_unit_code: str
    role_code: str
    required_audiences: tuple[str, ...]


_LOCAL_SERVICE_ACCOUNT_BINDINGS = (
    LocalServiceAccountBinding(
        client_id="lineageweave-test-automation",
        display_name="LineageWeave Test Automation",
        email_address="lineageweave-test-automation@example.test",
        process_unit_code="DEMO-PU-A",
        role_code="viewer",
        required_audiences=(LINEAGEWEAVE_API_AUDIENCE, LINEAGEWEAVE_MCP_AUDIENCE),
    ),
    LocalServiceAccountBinding(
        client_id="lineageweave-test-admin",
        display_name="LineageWeave Test Admin",
        email_address="lineageweave-test-admin@example.test",
        process_unit_code="DEMO-PU-HQ",
        role_code="admin",
        required_audiences=(LINEAGEWEAVE_API_AUDIENCE,),
    ),
)


def _machine_access_token_audiences(client: dict[str, object]) -> frozenset[str]:
    """Return exact custom audiences emitted into access tokens by this fixture."""
    protocol_mappers = client.get("protocolMappers")
    if not isinstance(protocol_mappers, list):
        return frozenset()

    audiences: set[str] = set()
    for mapper in protocol_mappers:
        if not isinstance(mapper, dict):
            continue
        if mapper.get("protocol") != "openid-connect":
            continue
        if mapper.get("protocolMapper") != "oidc-audience-mapper":
            continue
        config = mapper.get("config")
        if not isinstance(config, dict) or config.get("access.token.claim") != "true":
            continue
        audience = config.get("included.custom.audience")
        if (
            isinstance(audience, str)
            and audience
            and audience == audience.strip()
        ):
            audiences.add(audience)
    return frozenset(audiences)


def _validate_machine_client(
    client_id: str,
    client: dict[str, object],
    required_audiences: tuple[str, ...],
) -> None:
    """Require a usable local confidential client before DB authorization exists."""
    if client.get("enabled") is not True:
        raise RuntimeError(f"realm client {client_id!r} must be enabled")
    if client.get("protocol") != "openid-connect":
        raise RuntimeError(f"realm client {client_id!r} must use openid-connect")
    if client.get("publicClient") is not False:
        raise RuntimeError(f"realm client {client_id!r} must be confidential")
    if client.get("serviceAccountsEnabled") is not True:
        raise RuntimeError(f"realm client {client_id!r} must enable service accounts")
    if client.get("directAccessGrantsEnabled") is not False:
        raise RuntimeError(f"realm client {client_id!r} must disable direct access grants")
    if client.get("standardFlowEnabled") is not False:
        raise RuntimeError(f"realm client {client_id!r} must disable browser standard flow")
    if client.get("implicitFlowEnabled") is not False:
        raise RuntimeError(f"realm client {client_id!r} must disable implicit flow")
    secret = client.get("secret")
    if not isinstance(secret, str) or not secret.strip():
        raise RuntimeError(f"realm client {client_id!r} must declare a client secret")

    token_audiences = _machine_access_token_audiences(client)
    missing_audiences = [
        audience for audience in required_audiences if audience not in token_audiences
    ]
    if missing_audiences:
        raise RuntimeError(
            f"realm client {client_id!r} must map required access-token audience(s): "
            + ", ".join(missing_audiences)
        )


def load_local_service_accounts(
    realm_export_path: Path = DEFAULT_REALM_EXPORT_PATH,
) -> tuple[LocalServiceAccount, ...]:
    """Join usable local machine clients to disjoint realm-owned service subjects."""
    realm = json.loads(realm_export_path.read_text())
    users = realm.get("users")
    if not isinstance(users, list):
        raise RuntimeError("realm fixture must contain a users array")

    subjects: dict[str, str] = {}
    service_subject_owners: dict[str, str] = {}
    non_service_subjects: set[str] = set()
    for user in users:
        if not isinstance(user, dict):
            continue
        client_id = user.get("serviceAccountClientId")
        subject_id = user.get("id")
        if client_id is None:
            if isinstance(subject_id, str) and subject_id:
                non_service_subjects.add(subject_id)
            continue
        if not isinstance(client_id, str) or not client_id:
            raise RuntimeError("realm service account must declare a non-empty client id")
        if user.get("enabled") is not True:
            raise RuntimeError(f"realm service account {client_id!r} must be enabled")
        if not isinstance(subject_id, str) or not subject_id:
            raise RuntimeError(
                f"realm service account {client_id!r} must declare a non-empty subject id"
            )
        if client_id in subjects:
            raise RuntimeError(f"duplicate realm service account client id: {client_id}")
        prior_client_id = service_subject_owners.get(subject_id)
        if prior_client_id is not None:
            raise RuntimeError(
                "duplicate realm service account subject "
                f"{subject_id!r}: {prior_client_id!r} and {client_id!r}"
            )
        subjects[client_id] = subject_id
        service_subject_owners[subject_id] = client_id

    shared_subjects = set(service_subject_owners).intersection(non_service_subjects)
    if shared_subjects:
        shared_subject = sorted(shared_subjects)[0]
        raise RuntimeError(
            f"realm service account subject {shared_subject!r} collides with a non-service realm subject"
        )

    clients = realm.get("clients")
    if not isinstance(clients, list):
        raise RuntimeError("realm fixture must contain a clients array")
    required_client_ids = {
        binding.client_id for binding in _LOCAL_SERVICE_ACCOUNT_BINDINGS
    }
    client_configs: dict[str, dict[str, object]] = {}
    for client in clients:
        if not isinstance(client, dict):
            continue
        client_id = client.get("clientId")
        if client_id not in required_client_ids:
            continue
        if client_id in client_configs:
            raise RuntimeError(f"duplicate realm client configuration: {client_id}")
        client_configs[client_id] = client

    accounts: list[LocalServiceAccount] = []
    for binding in _LOCAL_SERVICE_ACCOUNT_BINDINGS:
        subject_id = subjects.get(binding.client_id)
        if subject_id is None:
            raise RuntimeError(
                f"realm fixture is missing service account {binding.client_id!r}"
            )
        client = client_configs.get(binding.client_id)
        if client is None:
            raise RuntimeError(
                f"realm fixture is missing {binding.client_id!r} client configuration"
            )
        _validate_machine_client(
            binding.client_id,
            client,
            binding.required_audiences,
        )
        accounts.append(
            LocalServiceAccount(
                client_id=binding.client_id,
                subject_id=subject_id,
                display_name=binding.display_name,
                email_address=binding.email_address,
                process_unit_code=binding.process_unit_code,
                role_code=binding.role_code,
            )
        )
    return tuple(accounts)


LOCAL_SERVICE_ACCOUNTS = load_local_service_accounts()


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

                    # Replace only this fixture actor's bindings so an earlier
                    # seed cannot retain broader authorization than the realm-backed contract.
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
