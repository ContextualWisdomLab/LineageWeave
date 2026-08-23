"""Tests for the fail-closed channel-weight operator boundary."""

from __future__ import annotations

import argparse
import asyncio
import runpy
import sys
from pathlib import Path

import pytest

import scripts.estimate_channel_weights as script


def test_operator_reports_the_missing_independent_anchor() -> None:
    with pytest.raises(RuntimeError, match="independent anchor"):
        asyncio.run(script._run(argparse.Namespace(post_limit=1, dry_run=True)))


def test_main_reports_an_authorized_result_when_the_boundary_supplies_one(
    monkeypatch,
    capsys,
) -> None:
    """The CLI serializes only the result returned by its policy boundary."""

    async def authorized_result(_args: argparse.Namespace) -> dict[str, object]:
        return {"available": False, "reason": "synthetic test boundary"}

    monkeypatch.setattr(script, "_run", authorized_result)
    monkeypatch.setattr(sys, "argv", [str(Path(script.__file__)), "--dry-run"])

    script.main()

    assert capsys.readouterr().out == (
        '{"available": false, "reason": "synthetic test boundary"}\n'
    )


def test_main_rejects_nonpositive_post_limit(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", [str(Path(script.__file__)), "--post-limit", "0"])
    with pytest.raises(SystemExit):
        script.main()


def test_module_entrypoint_fails_closed_before_reading_corpus(monkeypatch) -> None:
    script_path = Path(script.__file__)
    monkeypatch.setattr(sys, "argv", [str(script_path)])
    with pytest.raises(RuntimeError, match="nothing was written"):
        runpy.run_path(str(script_path), run_name="__main__")
