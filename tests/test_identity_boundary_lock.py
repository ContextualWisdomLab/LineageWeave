"""Lock the Compose worker to its model-proxy role."""

from __future__ import annotations

import importlib
import json
import subprocess
import threading
import urllib.error
import urllib.request
import pytest

from tests._contract_utils import (
    assert_http_error_contract,
    find_contract_route,
    load_contract,
)

_IDENTITY_BOUNDARY_CONTRACT = "compose_identity_boundary_contract.json"
_COMPOSE_BOUNDARY_GUARD = importlib.import_module("scripts.check_compose_identity_boundary")


def _load_identity_boundary_contract() -> dict:
    """Load identity-boundary contract expectations from resources."""
    return load_contract(_IDENTITY_BOUNDARY_CONTRACT)


def _load_compose_yaml() -> str:
    """Read compose yaml through the same script-scoped path used by the guard."""
    return _COMPOSE_BOUNDARY_GUARD.COMPOSE_YAML_PATH.read_text(encoding="utf-8")


def _load_worker():
    """Load the worker from the current checkout."""
    return importlib.reload(importlib.import_module("compose.http_standin"))


def test_compose_worker_excludes_local_keyverse_oidc() -> None:
    """Retain the audit artifact without importing or packaging it."""
    worker = _COMPOSE_BOUNDARY_GUARD.WORKER_PATH.read_text(encoding="utf-8")
    dockerfile = _COMPOSE_BOUNDARY_GUARD.WORKER_DOCKERFILE_PATH.read_text(encoding="utf-8")
    contract = _load_identity_boundary_contract()
    forbidden_fragments = tuple(contract["worker_package"]["forbidden_fragments"])
    assert _COMPOSE_BOUNDARY_GUARD.COMPOSE_ROOT.joinpath("compose/keyverse_oidc.py").exists()
    for fragment in forbidden_fragments:
        assert fragment not in worker
        assert fragment not in dockerfile


def test_compose_worker_rejects_all_identity_routes() -> None:
    """The worker must never become a discovery, authorization, or token server."""
    module = _load_worker()
    route_contract = load_contract("compose_oidc_worker_route_contract.json")
    httpd = module.ThreadingHTTPServer(("127.0.0.1", 0), module.StandinHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        for route in route_contract["routes"]:
            path = route["path"]
            method = route["method"]
            data = b"{}" if method == "POST" else None
            request = urllib.request.Request(
                origin + path,
                data=data,
                method=method,
            )
            try:
                urllib.request.urlopen(request, timeout=5)
                raise AssertionError(f"identity route unexpectedly served: {path}")
            except urllib.error.HTTPError as error:
                route_schema = find_contract_route(route_contract, path, method)
                assert_http_error_contract(
                    error.code,
                    json.loads(error.read()),
                    route_schema,
                )
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_compose_product_profile_disables_local_oidc_mode() -> None:
    """Only the worker clears identity values; the product can consume external ones."""
    compose_yaml = _load_compose_yaml()
    contract = _load_identity_boundary_contract()
    product_contract = contract["compose"]["product"]
    services = "\n" + compose_yaml
    product = services.split("\n  lineageweave:\n", 1)[1].split("\n  valkey:\n", 1)[0]
    worker = services.split("\n  lineage-http-standin:\n", 1)[1].split("\n  searxng:\n", 1)[0]
    for value in product_contract["required_enabled_lines"]:
        assert value in product
    assert "LINEAGEWEAVE_DSN: ${LINEAGEWEAVE_DSN:-}" in product
    assert "LINEAGE_SOURCE_TABLE: ${LINEAGE_SOURCE_TABLE:-}" in product
    for value in product_contract["forbidden_lines"]:
        assert value not in product
    for value in product_contract["required_absent_lines"]:
        assert value not in product
    forbidden_prefixes = tuple(product_contract["forbidden_prefixes"])
    for line in product.splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key = stripped.split(":", 1)[0].strip()
        if key.startswith(forbidden_prefixes) and '""' not in stripped:
            raise AssertionError("compose.yaml must not include forbidden identity environment key prefixes in product service")
    for value in contract["compose"]["worker"]["required_lines"]:
        assert value in worker
    for value in contract["compose"]["worker"]["required_absent_lines"]:
        assert value not in worker
    worker_forbidden_prefixes = tuple(contract["compose"]["worker"]["forbidden_prefixes"])
    for line in worker.splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key = stripped.split(":", 1)[0].strip()
        if key.startswith(worker_forbidden_prefixes) and '""' not in stripped:
            raise AssertionError("compose.yaml must not include forbidden identity environment key prefixes in worker service")


def test_compose_identity_boundary_guard_script() -> None:
    """The deployment guard script must pass in the current checkout."""
    completed = subprocess.run(
        ["python", "scripts/check_compose_identity_boundary.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout.strip() == "compose-keyverse-identity-boundary-guard-ok"


def test_compose_worker_rejects_identity_environment_variables(monkeypatch) -> None:
    """Prevent known and future Keyverse variables from reaching the standin."""
    module = _load_worker()
    contract = _load_identity_boundary_contract()
    for key in contract["worker_package"]["required_identity_keys"]:
        monkeypatch.setenv(key, "https://identity.example.com")
    with pytest.raises(RuntimeError, match="compose_standin_identity_variables_forbidden"):
        module._assert_identity_env_forbidden()


def test_compose_boundary_guard_catches_product_oidc_prefix(monkeypatch, tmp_path) -> None:
    """A non-empty forbidden OIDC prefix in product env must fail boundary checks."""
    guard = importlib.import_module("scripts.check_compose_identity_boundary")
    compose_yaml = """
name: lineageweavem2
services:
  lineageweave:
    LINEAGEWEAVE_HOST: 0.0.0.0
    LINEAGEWEAVE_PORT: 8000
    LINEAGEWEAVE_DSN: ""
    LINEAGE_SOURCE_TABLE: ""
    LINEAGEWEAVE_DEV_MODE: "0"
    LINEAGEWEAVE_COOKIE_SECURE: "1"
    LINEAGEWEAVE_DEV_ACTOR_JSON: ""
    LINEAGEWEAVE_VALKEY_URL: redis://valkey:6379/0
    LINEAGEWEAVE_COMPOSE_STANDIN_URL: http://lineage-http-standin:8080
    LINEAGEWEAVE_PRODUCT_LLM_TIMEOUT: ${LINEAGEWEAVE_PRODUCT_LLM_TIMEOUT:-120}
    LINEAGEWEAVE_REPORT_JUDGE_TIMEOUT: ${LINEAGEWEAVE_REPORT_JUDGE_TIMEOUT:-15}
    LINEAGEWEAVE_REPORT_REFRESH_MAX_SLICES: ${LINEAGEWEAVE_REPORT_REFRESH_MAX_SLICES:-3}
    LINEAGEWEAVE_REPORT_REFRESH_MAX_ATTEMPTS: ${LINEAGEWEAVE_REPORT_REFRESH_MAX_ATTEMPTS:-1}
    KEYMAN_MODEL: ${KEYMAN_MODEL:-gpt-4.1-mini}
    LINEAGEWEAVE_SEARXNG_URL: ${LINEAGEWEAVE_SEARXNG_URL:-http://searxng:8080}
    SEARXNG_CA_BUNDLE: ${SEARXNG_CA_BUNDLE:-}
    OIDC_CLIENT_ID: "disallowed"
    KEYVERSE_ISSUER: ""
    KEYVERSE_BASE_URL: ""
    KEYVERSE_CA_BUNDLE: ""
    KEYVERSE_ADMIN_TOKEN_URL: ""
    KEYVERSE_ADMIN_USERNAME: ""
    KEYVERSE_ADMIN_PASSWORD: ""
    KEYVERSE_REGISTRATION_URL: ""
    KEYVERSE_REGISTRATION_TOKEN: ""
    LINEAGEWEAVE_OIDC_CLIENT_ID: ""
    LINEAGEWEAVE_OIDC_CLIENT_SECRET: ""
    LINEAGEWEAVE_OIDC_REDIRECT_URI: ""
    environment:
      - "A=1"
  valkey:
    image: valkey/valkey:8-alpine
    command: ["valkey-server", "--appendonly", "yes"]
  lineage-http-standin:
    KEYVERSE_ISSUER: ""
    KEYVERSE_BASE_URL: ""
    KEYVERSE_CA_BUNDLE: ""
    KEYVERSE_ADMIN_TOKEN_URL: ""
    KEYVERSE_ADMIN_USERNAME: ""
    KEYVERSE_ADMIN_PASSWORD: ""
    KEYVERSE_REGISTRATION_URL: ""
    KEYVERSE_REGISTRATION_TOKEN: ""
    LINEAGEWEAVE_OIDC_CLIENT_ID: ""
    LINEAGEWEAVE_OIDC_CLIENT_SECRET: ""
    LINEAGEWEAVE_OIDC_REDIRECT_URI: ""
    env_file:
      - path: ${LINEAGEWEAVE_ENV_FILE:-${HOME}/.env}
  searxng:
    image: lineageweave-searxng:local
""".lstrip()
    compose_path = tmp_path / "compose.yaml"
    compose_path.write_text(compose_yaml, encoding="utf-8")
    monkeypatch.setattr(guard, "COMPOSE_YAML_PATH", compose_path, raising=False)
    with pytest.raises(AssertionError, match="product service should not expose boundary key in plain value: OIDC_CLIENT_ID: \\\"disallowed\\\""):
        guard._assert_compose_boundary()
