"""Shared test utilities for JSON contract validation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


_REPO_ROOT = Path(__file__).resolve().parents[1]
_RESOURCE_ROOT = _REPO_ROOT / "tests" / "resources"


@lru_cache(maxsize=32)
def load_contract(name: str) -> dict[str, Any]:
    """Load a JSON contract resource with memoization."""
    return json.loads((_RESOURCE_ROOT / name).read_text(encoding="utf-8"))


def assert_audit_event_contract(event: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    """Validate one audit event against a declarative contract."""
    event_name = str(event.get("event", ""))
    events = contract.get("events", {})
    assert event_name in events
    required_fields = set(events[event_name].get("required_fields", []))
    assert required_fields
    assert set(event.keys()) >= required_fields
    for field in required_fields:
        assert isinstance(event[field], str)
    for field, allowed in contract.get("field_constraints", {}).items():
        if field in event:
            assert event[field] in allowed


def find_contract_route(contract: Mapping[str, Any], path: str, method: str) -> Mapping[str, Any]:
    """Find the route contract by normalized path and method."""
    for route in contract.get("routes", []):
        if route.get("path") == path and route.get("method") == method:
            return route
    raise AssertionError(f"route contract missing for {method} {path}")


def assert_http_error_contract(
    response_status: int, response_body: Mapping[str, Any], contract: Mapping[str, Any]
) -> None:
    """Assert status and JSON body against route-level contract fields."""
    assert response_status == int(contract["expected_status"])
    assert dict(response_body) == dict(contract["expected_body"])
