"""Fail-closed orchestrator envelopes are not confidence scores (ADR 0014)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "lineageweave" / "orchestrator_envelope.py"


def _load():
    spec = importlib.util.spec_from_file_location("lw_orchestrator_envelope", _PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


env = _load()


def test_parse_returns_the_first_choice_text() -> None:
    text = env.parse_chat_completion(
        {"choices": [{"message": {"content": "0.81"}}], "id": "cmpl-1"}
    )
    assert text == "0.81"


def test_error_code_fails_closed_even_with_choices() -> None:
    try:
        env.parse_chat_completion(
            {
                "error_code": "invalid_mode",
                "message": "verify is not enabled",
                "choices": [{"message": {"content": "0.9"}}],
            }
        )
    except env.OrchestratorEnvelopeError as exc:
        assert exc.error_code == "invalid_mode"
    else:
        raise AssertionError("expected OrchestratorEnvelopeError")


def test_missing_choices_and_blank_content_fail_closed() -> None:
    for body in ({}, {"choices": []}, {"choices": [{"message": {"content": "  "}}]}, []):
        try:
            env.parse_chat_completion(body)
        except env.OrchestratorEnvelopeError:
            continue
        raise AssertionError(f"expected fail-closed for {body!r}")
