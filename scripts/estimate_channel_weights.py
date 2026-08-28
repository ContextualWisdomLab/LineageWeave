"""Fail closed until fast-mlsirm publishes fitted channel-weight artifacts.

ADR 0145 prohibits unanchored local estimation. The previous Python sampling,
2PL fitting, normalization, and persistence path is intentionally unavailable.
"""

from __future__ import annotations

import argparse
import asyncio

DETERMINISTIC_SET_CODE = "channel_set_deterministic"
_UNAVAILABLE = (
    "channel-weight estimation is unavailable until fast-mlsirm protected main "
    "publishes fitted, independently anchored owner evidence; nothing was written"
)


def estimator_version() -> str:
    """Return the pinned owner package version for diagnostics only."""
    from importlib.metadata import version

    return version("fast-mlsirm")


def source_snapshot_digest(rows: list) -> str:
    """Refuse the retired local estimation snapshot path."""
    del rows
    raise RuntimeError(_UNAVAILABLE)


def sample_pair_scores(records: list, *, window: int = 0) -> None:
    """Refuse local pair scoring for psychometric estimation."""
    del records, window
    raise RuntimeError(_UNAVAILABLE)


def subsample_stride(total: int, limit: int) -> None:
    """Refuse local estimation subsampling."""
    del total, limit
    raise RuntimeError(_UNAVAILABLE)


async def persist_estimate(*args, **kwargs) -> None:
    """Refuse every write without an accepted owner-fitted artifact."""
    del args, kwargs
    raise RuntimeError(_UNAVAILABLE)


async def _run(args: argparse.Namespace) -> None:
    """Fail before opening a database connection or performing arithmetic."""
    del args
    raise RuntimeError(_UNAVAILABLE)


def main() -> None:
    """Exit nonzero without computing or persisting local weights."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    asyncio.run(_run(argparse.Namespace()))


if __name__ == "__main__":
    main()
