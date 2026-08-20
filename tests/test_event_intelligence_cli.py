"""Executable dossier-validator tests."""

from __future__ import annotations

import json
from pathlib import Path

from lineageweave.event_intelligence_cli import main

ROOT = Path(__file__).parents[1]
EXAMPLE_PATH = ROOT / "examples" / "event-intelligence-dossier-v1.json"


def test_cli_validates_and_returns_machine_readable_receipt(capsys) -> None:
    """A valid dossier emits a stable receipt and exits successfully."""
    expected = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    assert main([str(EXAMPLE_PATH)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt == {
        "contract_version": 1,
        "dossier_sha256": expected["dossier_sha256"],
        "event_id": expected["event_id"],
        "status_code": "valid",
    }


def test_cli_fails_closed_for_missing_invalid_and_tampered_files(tmp_path, capsys) -> None:
    """I/O, JSON, and semantic failures are bounded nonzero outcomes."""
    assert main([str(tmp_path / "missing.json")]) == 2
    assert "validation_failed" in capsys.readouterr().err

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    assert main([str(malformed)]) == 2
    assert "validation_failed" in capsys.readouterr().err

    non_utf8 = tmp_path / "non-utf8.json"
    non_utf8.write_bytes(b"\xff")
    assert main([str(non_utf8)]) == 2
    assert "UTF-8" in capsys.readouterr().err

    tampered = tmp_path / "tampered.json"
    payload = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    payload["event_title"] = "tampered"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    assert main([str(tampered)]) == 2
    assert "dossier_sha256" in capsys.readouterr().err
