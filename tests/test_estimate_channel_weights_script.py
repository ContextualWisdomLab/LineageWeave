"""The retired local channel-weight operator must never write."""

from __future__ import annotations

import argparse
import asyncio

import pytest

import scripts.estimate_channel_weights as script


def test_operator_fails_before_database_or_local_estimation() -> None:
    with pytest.raises(RuntimeError, match="nothing was written"):
        asyncio.run(script._run(argparse.Namespace()))


def test_persistence_entry_point_always_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="nothing was written"):
        asyncio.run(script.persist_estimate(object()))


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (script.source_snapshot_digest, ([],)),
        (script.sample_pair_scores, ([],)),
        (script.subsample_stride, (10, 2)),
    ],
)
def test_retired_python_math_helpers_are_inert(function, args) -> None:
    with pytest.raises(RuntimeError, match="nothing was written"):
        function(*args)
