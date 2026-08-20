#!/usr/bin/env python3
"""Advance one pull-request stack by at most one fail-closed mutation.

The script retargets a child only after its predecessor merged, and merges only
when the exact head has terminal successful checks and an independent exact-head
approval. It never uses admin bypass, force merge, or self-approval.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from typing import Any

_ALLOWED_CHECK_CONCLUSIONS = {"success", "neutral", "skipped"}


def _run(arguments: Sequence[str], *, input_text: str | None = None) -> str:
    completed = subprocess.run(
        list(arguments),
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"{' '.join(arguments)} failed: {message}")
    return completed.stdout


def _gh_json(arguments: Sequence[str]) -> Any:
    output = _run(["gh", *arguments])
    return json.loads(output) if output.strip() else None


def _api(path: str, *, method: str = "GET", fields: dict[str, str] | None = None) -> Any:
    arguments = ["api", f"repos/{os.environ['GITHUB_REPOSITORY']}/{path}"]
    if method != "GET":
        arguments.extend(["--method", method])
    for name, value in (fields or {}).items():
        arguments.extend(["--field", f"{name}={value}"])
    return _gh_json(arguments)


def _exact_review_state(
    reviews: list[dict[str, Any]], *, head_sha: str, author_login: str
) -> tuple[list[str], list[str]]:
    latest_by_reviewer: dict[str, dict[str, Any]] = {}
    for review in reviews:
        user = review.get("user") or {}
        login = str(user.get("login") or "")
        if not login or login == author_login or review.get("commit_id") != head_sha:
            continue
        current = latest_by_reviewer.get(login)
        current_id = int(current.get("id") or 0) if current else -1
        review_id = int(review.get("id") or 0)
        if current is None or review_id >= current_id:
            latest_by_reviewer[login] = review
    approvals = sorted(
        login
        for login, review in latest_by_reviewer.items()
        if str(review.get("state") or "").upper() == "APPROVED"
    )
    changes = sorted(
        login
        for login, review in latest_by_reviewer.items()
        if str(review.get("state") or "").upper() == "CHANGES_REQUESTED"
    )
    return approvals, changes


def _check_gate(head_sha: str) -> dict[str, Any]:
    check_payload = _api(f"commits/{head_sha}/check-runs?per_page=100") or {}
    check_runs = list(check_payload.get("check_runs") or [])
    pending = sorted(
        str(run.get("name") or "unnamed")
        for run in check_runs
        if str(run.get("status") or "") != "completed"
    )
    failing = sorted(
        f"{run.get('name') or 'unnamed'}={run.get('conclusion')}"
        for run in check_runs
        if str(run.get("status") or "") == "completed"
        and str(run.get("conclusion") or "") not in _ALLOWED_CHECK_CONCLUSIONS
    )
    status_payload = _api(f"commits/{head_sha}/status") or {}
    statuses = list(status_payload.get("statuses") or [])
    combined_state = str(status_payload.get("state") or "")
    status_gate_ok = not statuses or combined_state == "success"
    return {
        "observed_check_count": len(check_runs),
        "pending_checks": pending,
        "failing_checks": failing,
        "combined_status": combined_state if statuses else "not_reported",
        "checks_ok": bool(check_runs) and not pending and not failing and status_gate_ok,
    }


def _merge_method(repository: dict[str, Any]) -> str:
    if repository.get("allow_merge_commit"):
        return "--merge"
    if repository.get("allow_squash_merge"):
        return "--squash"
    if repository.get("allow_rebase_merge"):
        return "--rebase"
    raise RuntimeError("repository exposes no supported pull-request merge method")


def _record_for_pull(pull: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": pull.get("number"),
        "state": pull.get("state"),
        "draft": pull.get("draft"),
        "merged_at": pull.get("merged_at"),
        "base_ref": (pull.get("base") or {}).get("ref"),
        "head_ref": (pull.get("head") or {}).get("ref"),
        "head_sha": (pull.get("head") or {}).get("sha"),
        "mergeable": pull.get("mergeable"),
        "mergeable_state": pull.get("mergeable_state"),
    }


def advance(stack: list[int]) -> dict[str, Any]:
    repository = _api("")
    default_branch = str(repository["default_branch"])
    merge_flag = _merge_method(repository)
    result: dict[str, Any] = {
        "repository": os.environ["GITHUB_REPOSITORY"],
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "default_branch": default_branch,
        "stack": stack,
        "action": "none",
        "pulls": [],
    }

    predecessor: dict[str, Any] | None = None
    for number in stack:
        pull = _api(f"pulls/{number}")
        record = _record_for_pull(pull)
        result["pulls"].append(record)

        if pull.get("merged_at"):
            predecessor = pull
            continue
        if str(pull.get("state") or "").lower() != "open":
            record["blockers"] = ["pull request is closed without merge"]
            result["blocked_at"] = number
            return result

        desired_base = default_branch
        if predecessor is not None and not predecessor.get("merged_at"):
            desired_base = str((predecessor.get("head") or {}).get("ref") or "")

        current_base = str((pull.get("base") or {}).get("ref") or "")
        if current_base != desired_base:
            _api(
                f"pulls/{number}",
                method="PATCH",
                fields={"base": desired_base},
            )
            result["action"] = "retargeted"
            result["action_pull"] = number
            result["old_base"] = current_base
            result["new_base"] = desired_base
            return result

        if predecessor is not None and not predecessor.get("merged_at"):
            record["blockers"] = [f"predecessor #{predecessor['number']} is not merged"]
            result["blocked_at"] = number
            return result

        head_sha = str((pull.get("head") or {}).get("sha") or "")
        author_login = str((pull.get("user") or {}).get("login") or "")
        reviews = _api(f"pulls/{number}/reviews?per_page=100") or []
        approvals, changes = _exact_review_state(
            reviews, head_sha=head_sha, author_login=author_login
        )
        checks = _check_gate(head_sha)
        record.update(checks)
        record["exact_head_approvals"] = approvals
        record["exact_head_changes_requested"] = changes

        blockers: list[str] = []
        if pull.get("draft"):
            blockers.append("pull request is draft")
        if pull.get("mergeable") is not True:
            blockers.append(f"mergeable={pull.get('mergeable')}")
        if str(pull.get("mergeable_state") or "") != "clean":
            blockers.append(f"mergeable_state={pull.get('mergeable_state')}")
        if not checks["checks_ok"]:
            blockers.append("exact-head checks are not terminal-success")
        if not approvals:
            blockers.append("independent exact-head approval is missing")
        if changes:
            blockers.append("exact-head changes-requested review exists")
        record["blockers"] = blockers
        if blockers:
            result["blocked_at"] = number
            return result

        _run(
            [
                "gh",
                "pr",
                "merge",
                str(number),
                merge_flag,
                "--delete-branch=false",
                "--repo",
                os.environ["GITHUB_REPOSITORY"],
            ]
        )
        result["action"] = "merged"
        result["action_pull"] = number
        result["merge_method"] = merge_flag.removeprefix("--")
        return result

    result["complete"] = True
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", required=True, help="Comma-separated PR numbers")
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    stack = [int(value) for value in arguments.stack.split(",") if value.strip()]
    if not stack:
        raise SystemExit("stack must not be empty")
    try:
        result = advance(stack)
    except Exception as exc:
        result = {
            "repository": os.environ.get("GITHUB_REPOSITORY", "unknown"),
            "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "stack": stack,
            "action": "error",
            "error": str(exc),
        }
        with open(arguments.output, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(json.dumps(result, indent=2), file=sys.stderr)
        raise
    with open(arguments.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
