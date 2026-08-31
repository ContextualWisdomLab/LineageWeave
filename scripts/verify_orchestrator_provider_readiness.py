#!/usr/bin/env python3
"""Verify configured-gateway readiness inside an isolated orchestrator container."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from typing import Any


_REQUEST_SCRIPT = r"""
import os
import sys
import urllib.error
import urllib.request

method, path, body, timeout_ms = sys.argv[1:]
headers = {"Authorization": f"Bearer {os.environ['CONTEXTUAL_ORCHESTRATOR_TOKEN']}"}
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
    """Require one structured-ready configured-gateway agent before promotion."""
    deadline = time.monotonic() + readiness_timeout

    def remaining_ms() -> int:
        remaining = int((deadline - time.monotonic()) * 1000)
        if remaining <= 0:
            raise RuntimeError("provider readiness exceeded its observation budget")
        return remaining

    cached = _request(
        container,
        "GET",
        "/api/v1/provider_readiness/latest",
        None,
        remaining_ms(),
    )
    items = cached.get("items")
    if not isinstance(items, list):
        raise RuntimeError("provider readiness catalog was unavailable")
    agent_ids = sorted(
        {
            item["agent_id"]
            for item in items
            if isinstance(item, dict)
            and item.get("provider") == "configured_gateway"
            and item.get("status") != "disabled"
            and isinstance(item.get("agent_id"), str)
            and item["agent_id"]
        }
    )
    if not agent_ids:
        raise RuntimeError("no active configured-gateway agent was discovered")
    job = _request(
        container,
        "POST",
        "/api/v1/provider_readiness_refreshes",
        {
            "agent_ids": agent_ids,
            "capability_code": "structured",
            "timeout_seconds": probe_timeout,
        },
        remaining_ms(),
    )
    job_id = job.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise RuntimeError("provider readiness job identity was unavailable")
    while True:
        status = job.get("status")
        if status == "completed":
            if (
                not isinstance(job.get("ready_count"), int)
                or job["ready_count"] <= 0
            ):
                raise RuntimeError(
                    "configured gateway did not authenticate for structured traffic"
                )
            return
        if status in {"failed", "cancelled", "expired"}:
            raise RuntimeError("configured gateway readiness failed")
        if status not in {"queued", "running"}:
            raise RuntimeError("provider readiness returned an unsupported state")
        poll_after_ms = job.get("poll_after_ms")
        if (
            not isinstance(poll_after_ms, int)
            or isinstance(poll_after_ms, bool)
            or poll_after_ms <= 0
        ):
            raise RuntimeError("provider readiness did not declare its polling cadence")
        if poll_after_ms >= remaining_ms():
            raise RuntimeError("provider readiness exceeded its observation budget")
        time.sleep(poll_after_ms / 1000)
        job = _request(
            container,
            "GET",
            f"/api/v1/provider_readiness_refreshes/{job_id}",
            None,
            remaining_ms(),
        )


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
