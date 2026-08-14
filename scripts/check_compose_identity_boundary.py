#!/usr/bin/env python3
"""Verify the compose profile cannot accidentally become a Keyverse-like IdP."""

from __future__ import annotations

from functools import lru_cache

import json
from pathlib import Path


CONTRACT_PATH = (
    Path(__file__).resolve().parent.parent / "tests" / "resources" / "compose_identity_boundary_contract.json"
)
COMPOSE_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_YAML_PATH = COMPOSE_ROOT / "compose.yaml"
WORKER_PATH = COMPOSE_ROOT / "compose" / "http_standin.py"
WORKER_DOCKERFILE_PATH = COMPOSE_ROOT / "compose" / "Dockerfile"


@lru_cache(maxsize=1)
def _load_identity_boundary_contract() -> dict:
    """Load compose identity-boundary expectations from repository resources."""
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _compose_contract() -> dict:
    """Return contract sections used by boundary assertions."""
    contract = _load_identity_boundary_contract()
    return contract["compose"]


def _worker_compose_block(compose: str) -> str:
    """Return the bounded worker service block from the checked Compose file."""
    _before, marker, remaining = ("\n" + compose).partition("\n  lineage-http-standin:\n")
    if not marker:
        raise AssertionError("compose.yaml has no lineage-http-standin service")
    worker, marker, _after = remaining.partition("\n  searxng:\n")
    if not marker:
        raise AssertionError("compose.yaml cannot bound the lineage-http-standin service")
    return worker


def _assert_compose_boundary() -> None:
    compose = COMPOSE_YAML_PATH.read_text(encoding="utf-8")
    contract = _compose_contract()
    forbidden_fragments = tuple(_load_identity_boundary_contract()["worker_package"]["forbidden_fragments"])
    if any(fragment in compose for fragment in forbidden_fragments):
        raise AssertionError("compose.yaml must not reference keyverse_oidc module or handlers")
    worker = _worker_compose_block(compose)
    services = "\n" + compose
    product = services.split("\n  lineageweave:\n", 1)[1].split("\n  valkey:\n", 1)[0]
    forbidden_prefixes = tuple(contract["product"]["forbidden_prefixes"])
    for value in contract["product"]["required_enabled_lines"]:
        if value not in product:
            raise AssertionError(f"product service missing required Keyverse boundary hardening: {value}")
    for value in contract["product"]["forbidden_lines"]:
        if value in product:
            raise AssertionError(f"product service should not interpolate Keyverse boundary variables: {value}")
    for value in contract["product"]["required_absent_lines"]:
        if value in product:
            raise AssertionError(f"product service should not expose boundary key in plain value: {value}")
    for line in product.splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key = stripped.split(":", 1)[0].strip()
        if key.startswith(forbidden_prefixes) and '""' not in stripped:
            raise AssertionError("compose.yaml must not include forbidden identity environment key prefixes in product service")
    worker_contract = contract["worker"]
    worker_required_lines = tuple(worker_contract["required_lines"])
    missing = [value for value in worker_required_lines if value not in worker]
    if missing:
        raise AssertionError(f"worker service missing Keyverse boundary hardening: {missing}")
    for value in worker_contract.get("required_absent_lines", ()):
        if value in worker:
            raise AssertionError(f"worker service must not include {value}")
    worker_forbidden_prefixes = tuple(worker_contract.get("forbidden_prefixes", ()))
    for line in worker.splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key = stripped.split(":", 1)[0].strip()
        if key.startswith(worker_forbidden_prefixes) and '""' not in stripped:
            raise AssertionError("compose.yaml must not include forbidden identity environment key prefixes in worker service")


def _assert_worker_boundary() -> None:
    worker = WORKER_PATH.read_text(encoding="utf-8")
    dockerfile = WORKER_DOCKERFILE_PATH.read_text(encoding="utf-8")
    if "keyverse_oidc" in worker:
        raise AssertionError("compose/http_standin.py must not contain keyverse OIDC handler logic")
    if "keyverse_oidc.py" in dockerfile:
        raise AssertionError("compose/Dockerfile must not import compose/keyverse_oidc.py")


def main() -> int:
    _assert_compose_boundary()
    _assert_worker_boundary()
    print("compose-keyverse-identity-boundary-guard-ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        raise SystemExit(str(error))
