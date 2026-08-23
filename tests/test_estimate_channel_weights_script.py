"""Tests for the fail-closed channel-weight operator boundary."""

from __future__ import annotations

import argparse
import asyncio

import pytest

import scripts.estimate_channel_weights as script


def test_operator_reports_the_missing_independent_anchor() -> None:
    with pytest.raises(RuntimeError, match="independent anchor"):
        asyncio.run(script._run(argparse.Namespace(post_limit=1, dry_run=True)))
