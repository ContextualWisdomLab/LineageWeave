"""Contracts for DB-owned authorization of local confidential test clients."""

import json
from pathlib import Path

import pytest

from scripts.provision_local_service_accounts import (
    LOCAL_SERVICE_ACCOUNTS,
    load_local_service_accounts,
)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_VALID_SERVICE_CLIENTS = [
    {
        "clientId": "lineageweave-test-automation",
        "enabled": True,
        "publicClient": False,
        "protocol": "openid-connect",
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": True,
    },
    {
        "clientId": "lineageweave-test-admin",
        "enabled": True,
        "publicClient": False,
        "protocol": "openid-connect",
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": True,
    },
]


def _write_realm(path: Path, users: object, clients: object | None = None) -> Path:
    path.write_text(
        json.dumps(
            {
                "users": users,
                "clients": _VALID_SERVICE_CLIENTS if clients is None else clients,
            }
        )
    )
    return path


def _service_users() -> list[dict[str, str]]:
    return [
        {
            "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "serviceAccountClientId": "lineageweave-test-automation",
        },
        {
            "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "serviceAccountClientId": "lineageweave-test-admin",
        },
    ]


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


def test_service_subjects_are_loaded_from_the_realm_fixture(tmp_path: Path) -> None:
    """A changed realm subject must flow into DB provisioning without a copied constant."""
    realm_path = _write_realm(tmp_path / "realm-export.json", _service_users())

    accounts = {
        account.client_id: account
        for account in load_local_service_accounts(realm_path)
    }

    assert accounts["lineageweave-test-automation"].subject_id == (
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    )
    assert accounts["lineageweave-test-admin"].subject_id == (
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    )


def test_service_subject_loader_fails_closed_when_a_required_actor_is_missing(
    tmp_path: Path,
) -> None:
    realm_path = _write_realm(
        tmp_path / "realm-export.json",
        [
            {
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "serviceAccountClientId": "lineageweave-test-automation",
            }
        ],
    )

    with pytest.raises(RuntimeError, match="lineageweave-test-admin"):
        load_local_service_accounts(realm_path)


def test_service_subject_loader_rejects_duplicate_client_identity(tmp_path: Path) -> None:
    realm_path = _write_realm(
        tmp_path / "realm-export.json",
        [
            {
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "serviceAccountClientId": "lineageweave-test-automation",
            },
            {
                "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                "serviceAccountClientId": "lineageweave-test-automation",
            },
            {
                "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "serviceAccountClientId": "lineageweave-test-admin",
            },
        ],
    )

    with pytest.raises(RuntimeError, match="duplicate realm service account"):
        load_local_service_accounts(realm_path)


def test_service_subject_loader_rejects_shared_subject_between_service_clients(
    tmp_path: Path,
) -> None:
    realm_path = _write_realm(
        tmp_path / "realm-export.json",
        [
            {
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "serviceAccountClientId": "lineageweave-test-automation",
            },
            {
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "serviceAccountClientId": "lineageweave-test-admin",
            },
        ],
    )

    with pytest.raises(RuntimeError, match="duplicate realm service account subject"):
        load_local_service_accounts(realm_path)


def test_service_subject_loader_rejects_human_subject_collision(tmp_path: Path) -> None:
    users: list[dict[str, str]] = [
        {
            "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "username": "demo.human",
        },
        *_service_users(),
    ]
    realm_path = _write_realm(tmp_path / "realm-export.json", users)

    with pytest.raises(RuntimeError, match="collides with a non-service realm subject"):
        load_local_service_accounts(realm_path)


def test_service_subject_loader_rejects_non_array_users(tmp_path: Path) -> None:
    realm_path = _write_realm(tmp_path / "realm-export.json", {"not": "an array"})

    with pytest.raises(RuntimeError, match="users array"):
        load_local_service_accounts(realm_path)


def test_service_subject_loader_rejects_missing_subject_id(tmp_path: Path) -> None:
    realm_path = _write_realm(
        tmp_path / "realm-export.json",
        [
            {"serviceAccountClientId": "lineageweave-test-automation"},
            {
                "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "serviceAccountClientId": "lineageweave-test-admin",
            },
        ],
    )

    with pytest.raises(RuntimeError, match="non-empty subject id"):
        load_local_service_accounts(realm_path)


def test_service_subject_loader_rejects_non_array_clients(tmp_path: Path) -> None:
    realm_path = _write_realm(
        tmp_path / "realm-export.json",
        _service_users(),
        clients={"not": "an array"},
    )

    with pytest.raises(RuntimeError, match="clients array"):
        load_local_service_accounts(realm_path)


def test_service_subject_loader_rejects_missing_client_configuration(tmp_path: Path) -> None:
    """A realm user alone must not turn an absent OAuth client into a machine actor."""
    realm_path = _write_realm(
        tmp_path / "realm-export.json",
        _service_users(),
        clients=[_VALID_SERVICE_CLIENTS[0]],
    )

    with pytest.raises(RuntimeError, match="lineageweave-test-admin.*client configuration"):
        load_local_service_accounts(realm_path)


def test_service_subject_loader_rejects_duplicate_client_configuration(tmp_path: Path) -> None:
    clients = [
        dict(_VALID_SERVICE_CLIENTS[0]),
        dict(_VALID_SERVICE_CLIENTS[0]),
        dict(_VALID_SERVICE_CLIENTS[1]),
    ]
    realm_path = _write_realm(
        tmp_path / "realm-export.json",
        _service_users(),
        clients=clients,
    )

    with pytest.raises(RuntimeError, match="duplicate realm client configuration"):
        load_local_service_accounts(realm_path)


@pytest.mark.parametrize(
    ("field", "invalid_value", "message"),
    [
        ("enabled", False, "must be enabled"),
        ("protocol", "saml", "must use openid-connect"),
        ("publicClient", True, "must be confidential"),
        ("serviceAccountsEnabled", False, "must enable service accounts"),
        ("directAccessGrantsEnabled", True, "must disable direct access grants"),
        ("standardFlowEnabled", True, "must disable browser standard flow"),
    ],
)
def test_service_subject_loader_rejects_non_machine_client_configuration(
    tmp_path: Path,
    field: str,
    invalid_value: object,
    message: str,
) -> None:
    """DB machine principals require the realm client to remain machine-only."""
    clients = [dict(client) for client in _VALID_SERVICE_CLIENTS]
    clients[0][field] = invalid_value
    realm_path = _write_realm(
        tmp_path / "realm-export.json",
        _service_users(),
        clients=clients,
    )

    with pytest.raises(RuntimeError, match=message):
        load_local_service_accounts(realm_path)


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
