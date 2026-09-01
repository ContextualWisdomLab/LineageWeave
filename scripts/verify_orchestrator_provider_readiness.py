#!/usr/bin/env python3
"""Verify configured-gateway readiness inside an isolated orchestrator container."""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any


_REQUEST_SCRIPT = r"""
import os
import sys
import urllib.error
import urllib.request

method, path, body, timeout_ms = sys.argv[1:]
headers = {
    "Authorization": f"Bearer {os.environ['CONTEXTUAL_ORCHESTRATOR_ADMIN_TOKEN']}"
}
data = None
if body:
    headers["Content-Type"] = "application/json"
    data = body.encode("utf-8")
headers["X-Request-Timeout-Ms"] = timeout_ms
request = urllib.request.Request(
    f"http://127.0.0.1:8000{path}", data=data, headers=headers, method=method
)
try:
    with urllib.request.urlopen(
        request, timeout=max(float(timeout_ms) / 1000, 1.0)
    ) as response:
        sys.stdout.write(response.read().decode("utf-8"))
except (OSError, urllib.error.HTTPError):
    raise SystemExit(1) from None
"""


def _request(
    container: str,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    timeout_ms: int,
) -> dict[str, Any]:
    """Call the authenticated local admin boundary without exporting its token."""
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            container,
            "python",
            "-",
            method,
            path,
            json.dumps(body) if body else "",
            str(timeout_ms),
        ],
        input=_REQUEST_SCRIPT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("orchestrator readiness request failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("orchestrator readiness response was not JSON") from None
    if not isinstance(payload, dict):
        raise RuntimeError("orchestrator readiness response was not an object")
    return payload


def verify(container: str, probe_timeout: float, readiness_timeout: int) -> None:
    """Require one ready configured-gateway agent before promotion."""
    del probe_timeout  # validated CLI compatibility; upstream owns probe duration
    report = _request(
        container,
        "GET",
        "/api/v1/provider_readiness/latest?refresh=true",
        None,
        readiness_timeout * 1000,
    )
    items = report.get("items")
    if not isinstance(items, list):
        raise RuntimeError("provider readiness catalog was unavailable")
    if not any(
        isinstance(item, dict)
        and item.get("provider") == "configured_gateway"
        and item.get("status") == "ready"
        for item in items
    ):
        raise RuntimeError("configured gateway did not authenticate")


def main() -> None:
    """Parse bounded operator inputs and perform the fail-closed verification."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--probe-timeout-seconds", required=True, type=float)
    parser.add_argument("--readiness-timeout-seconds", required=True, type=int)
    args = parser.parse_args()
    if not 0.1 <= args.probe_timeout_seconds <= 30:
        parser.error("probe timeout must be between 0.1 and 30 seconds")
    if args.readiness_timeout_seconds <= 0:
        parser.error("readiness timeout must be positive")
    try:
        verify(args.container, args.probe_timeout_seconds, args.readiness_timeout_seconds)
    except RuntimeError as exc:
        raise SystemExit(f"preflight failed: {exc}") from None


if __name__ == "__main__":
    main()
