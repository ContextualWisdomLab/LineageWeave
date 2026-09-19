"""Contracts for DB-owned authorization of local confidential test clients."""

import json
from pathlib import Path

from scripts.provision_local_service_accounts import LOCAL_SERVICE_ACCOUNTS


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_service_accounts_are_distinct_and_least_privilege() -> None:
    """Automation and admin clients resolve to different normalized actors."""
    by_name = {account.client_id: account for account in LOCAL_SERVICE_ACCOUNTS}

    automation = by_name["lineageweave-test-automation"]
    admin = by_name["lineageweave-test-admin"]

    assert automation.subject_id == "33333333-3333-4333-8333-333333333333"
    assert automation.process_unit_code == "DEMO-PU-A"
    assert automation.role_code == "viewer"
    assert admin.subject_id == "44444444-4444-4444-8444-444444444444"
    assert admin.process_unit_code == "DEMO-PU-HQ"
    assert admin.role_code == "admin"
    assert automation.subject_id != admin.subject_id


def test_normalized_subjects_match_confidential_realm_service_accounts() -> None:
    """DB bindings consume the realm fixture's subjects instead of inventing ids."""
    realm = json.loads(
        (_REPO_ROOT / "docker" / "keycloak" / "realm-export.json").read_text()
    )
    realm_subjects = {
        user["serviceAccountClientId"]: user["id"]
        for user in realm["users"]
        if user.get("serviceAccountClientId")
    }
    by_name = {account.client_id: account for account in LOCAL_SERVICE_ACCOUNTS}

    assert set(by_name) == {
        "lineageweave-test-automation",
        "lineageweave-test-admin",
    }
    assert {
        client_id: account.subject_id for client_id, account in by_name.items()
    } == {
        client_id: realm_subjects[client_id] for client_id in by_name
    }

    clients = {client["clientId"]: client for client in realm["clients"]}
    for client_id in by_name:
        client = clients[client_id]
        assert client["publicClient"] is False
        assert client["directAccessGrantsEnabled"] is False
        assert client["serviceAccountsEnabled"] is True


def test_local_service_account_provisioner_does_not_authenticate_to_keycloak() -> None:
    """DB authorization provisioning must not reintroduce an identity grant."""
    source = (_REPO_ROOT / "scripts" / "provision_local_service_accounts.py").read_text()

    assert "grant_type" not in source
    assert "KEYCLOAK_ADMIN" not in source
    assert "post_form" not in source


def test_make_seed_provisions_service_accounts_after_demo_domain_rows() -> None:
    """The normalized actors are created only after their corp/PU/roles exist."""
    makefile = (_REPO_ROOT / "Makefile").read_text()
    human_seed = "python scripts/seed_demo_data.py"
    service_seed = "python scripts/provision_local_service_accounts.py"

    assert human_seed in makefile
    assert service_seed in makefile
    assert makefile.index(human_seed) < makefile.index(service_seed)
