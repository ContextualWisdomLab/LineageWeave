"""Fail-closed operator boundary for lineage channel weights (ADR 0145).

No independent lineage anchor is currently authorized, so this command does
not query the corpus, fit a model, or write weights.
"""

from __future__ import annotations

import argparse
import asyncio
import json


async def _run(_args: argparse.Namespace) -> dict[str, object]:
    raise RuntimeError(
        "lineage channel-weight estimation is unavailable until an independent anchor "
        "and accepted ADR authorize it; no corpus data was read and nothing was written"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--post-limit",
        type=int,
        default=5000,
        help="Maximum eligible posts to sample pairs from (default: 5000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Estimate and report, but persist nothing",
    )
    args = parser.parse_args()
    if args.post_limit < 1:
        parser.error("--post-limit must be positive")
    print(json.dumps(asyncio.run(_run(args)), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
