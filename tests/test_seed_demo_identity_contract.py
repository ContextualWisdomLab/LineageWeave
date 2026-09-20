"""Keep synthetic seed/bootstrap identity off resource-owner password grants."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SEED_SCRIPT = ROOT / "scripts" / "seed_demo_data.py"
WARM_SCRIPT = ROOT / "scripts" / "warm_seeded_post_content.py"
MAKEFILE = ROOT / "Makefile"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _realm(users: list[dict[str, object]]) -> dict[str, object]:
    return {"realm": "lineageweave-demo", "users": users}


def test_seed_subjects_are_read_from_realm_fixture_without_admin_login(tmp_path: Path) -> None:
    seed = _load_script(SEED_SCRIPT, "seed_demo_data_contract")
    fixture = tmp_path / "realm-export.json"
    fixture.write_text(
        json.dumps(
            _realm(
                [
                    {"id": "analyst-sub", "username": "demo.analyst", "enabled": True},
                    {"id": "admin-sub", "username": "demo.admin", "enabled": True},
                ]
            )
        ),
        encoding="utf-8",
    )

    assert seed._load_demo_user_subjects(fixture) == {
        "demo.analyst": "analyst-sub",
        "demo.admin": "admin-sub",
    }


@pytest.mark.parametrize(
    "users, message",
    [
        ([{"id": "analyst-sub", "username": "demo.analyst", "enabled": True}], "missing"),
        (
            [
                {"id": "same-sub", "username": "demo.analyst", "enabled": True},
                {"id": "same-sub", "username": "demo.admin", "enabled": True},
            ],
            "subject",
        ),
        (
            [
                {"id": "analyst-sub", "username": "demo.analyst", "enabled": False},
                {"id": "admin-sub", "username": "demo.admin", "enabled": True},
            ],
            "enabled",
        ),
    ],
)
def test_seed_subject_fixture_fails_closed(
    tmp_path: Path, users: list[dict[str, object]], message: str
) -> None:
    seed = _load_script(SEED_SCRIPT, f"seed_demo_data_contract_{message}")
    fixture = tmp_path / "realm-export.json"
    fixture.write_text(json.dumps(_realm(users)), encoding="utf-8")

    with pytest.raises(RuntimeError, match=message):
        seed._load_demo_user_subjects(fixture)


def test_seed_and_warm_scripts_contain_no_resource_owner_password_grant() -> None:
    seed_source = SEED_SCRIPT.read_text(encoding="utf-8")
    warm_source = WARM_SCRIPT.read_text(encoding="utf-8")

    assert '"grant_type": "password"' not in seed_source
    assert "admin-cli" not in seed_source
    assert "KEYCLOAK_ADMIN_PASSWORD" not in seed_source
    assert '"grant_type": "password"' not in warm_source
    assert '"grant_type": "client_credentials"' in warm_source
    assert "demo.analyst" not in warm_source
    assert "LINEAGEWEAVE_DEMO_USER_PASSWORD" not in warm_source


def test_warmup_uses_confidential_automation_client(monkeypatch: pytest.MonkeyPatch) -> None:
    warm = _load_script(WARM_SCRIPT, "warm_seeded_post_content_contract")
    observed: dict[str, object] = {}

    def fake_post_form(url: str, fields: dict[str, str], *, timeout: float):
        observed.update({"url": url, "fields": fields, "timeout": timeout})
        return {"access_token": "machine-token"}

    monkeypatch.setattr(warm, "post_form", fake_post_form)

    assert warm._machine_access_token("http://localhost:18080", "secret") == "machine-token"
    assert observed["fields"] == {
        "grant_type": "client_credentials",
        "client_id": "lineageweave-test-automation",
        "client_secret": "secret",
    }


def test_make_seed_orders_fixture_then_authorization_then_machine_warmup() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    seed_block = makefile.split("seed:\n", 1)[1].split("\n\n# Authenticated Compose", 1)[0]

    assert "KEYCLOAK_ADMIN_PASSWORD" not in seed_block
    assert "KEYCLOAK_CLIENT_SECRET is required" in seed_block
    commands = [
        "python scripts/seed_demo_data.py",
        "python scripts/provision_local_service_accounts.py",
        "python scripts/warm_seeded_post_content.py",
    ]
    positions = [seed_block.index(command) for command in commands]
    assert positions == sorted(positions)
