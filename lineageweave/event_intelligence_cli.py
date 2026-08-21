"""Command-line validation for Event Intelligence Dossier v1 artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from .event_intelligence import (
    EventIntelligenceValidationError,
    event_intelligence_dossier_from_dict,
)


def _parser() -> argparse.ArgumentParser:
    """Build the bounded command-line parser."""
    parser = argparse.ArgumentParser(
        prog="lineageweave-validate-event-intelligence",
        description="Validate and verify an Event Intelligence Dossier v1 JSON artifact.",
    )
    parser.add_argument("dossier", type=Path, help="Path to the dossier JSON file")
    return parser


def _write_json(stream: TextIO, value: dict[str, object]) -> None:
    """Write one deterministic JSON object followed by a newline."""
    stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")))
    stream.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Validate a dossier and emit a machine-readable receipt.

    Returns ``0`` for a valid, digest-matching dossier and ``2`` for bounded
    input, JSON, or contract validation failures. Error output may include a
    bounded field path or violation identifier to guide correction, but never
    includes dossier source text or a Python traceback.
    """
    args = _parser().parse_args(argv)
    try:
        raw = args.dossier.read_text(encoding="utf-8")
    except OSError:
        message = "unable to read dossier"
    except UnicodeError:
        message = "dossier must be UTF-8"
    else:
        try:
            payload = json.loads(raw)
            dossier = event_intelligence_dossier_from_dict(payload)
        except json.JSONDecodeError:
            message = "dossier JSON is invalid"
        except EventIntelligenceValidationError as exc:
            message = str(exc)
        else:
            _write_json(
                sys.stdout,
                {
                    "contract_version": dossier.contract_version,
                    "dossier_sha256": dossier.dossier_sha256(),
                    "event_id": dossier.event_id,
                    "status_code": "valid",
                },
            )
            return 0
    _write_json(
        sys.stderr,
        {
            "error_code": "validation_failed",
            "message": message,
            "status_code": "invalid",
        },
    )
    return 2


if __name__ == "__main__":  # pragma: no cover - exercised through the console entry point
    raise SystemExit(main())
