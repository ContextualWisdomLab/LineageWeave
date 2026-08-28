"""The retired LLM channel-weight workflow must remain inert."""

from __future__ import annotations

import argparse
import asyncio

import pytest

import scripts.estimate_llm_channel_weights as script


def test_workflow_fails_before_submission_or_persistence() -> None:
    with pytest.raises(RuntimeError, match="nothing was submitted or written"):
        asyncio.run(script._run(argparse.Namespace()))
