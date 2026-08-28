"""Fail closed for the retired local LLM channel-weight workflow.

Provider calls remain owned by contextual-orchestrator, but no batch result is
converted into a LineageWeave-local weight. A replacement requires a fitted,
independently anchored fast-mlsirm owner artifact.
"""

from __future__ import annotations

import argparse
import asyncio

_UNAVAILABLE = (
    "LLM channel-weight estimation is unavailable until fast-mlsirm protected "
    "main publishes fitted owner evidence; nothing was submitted or written"
)


async def _run(args: argparse.Namespace) -> None:
    """Fail before provider submission, database access, or local arithmetic."""
    del args
    raise RuntimeError(_UNAVAILABLE)


def main() -> None:
    """Exit nonzero without submitting or persisting an estimation job."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    asyncio.run(_run(argparse.Namespace()))


if __name__ == "__main__":
    main()
