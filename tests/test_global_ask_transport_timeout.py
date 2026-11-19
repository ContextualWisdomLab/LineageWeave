"""Regression contracts for the optional Global Ask transport timeout."""

from __future__ import annotations

import pytest

from backend.app.config import _validated_answer_timeout


def test_explicit_transport_timeout_is_not_coupled_to_removed_worker_deadline() -> None:
    """A finite positive transport timeout is independent of worker liveness."""
    assert _validated_answer_timeout("900") == 900.0


def test_explicit_transport_timeout_rejects_non_positive_or_non_finite_values() -> None:
    """Explicit transport limits must be finite and strictly positive."""
    for raw in ("0", "-1", "nan", "inf", "-inf"):
        with pytest.raises(ValueError):
            _validated_answer_timeout(raw)


def test_omitted_or_blank_transport_timeout_remains_null() -> None:
    """No configured timeout means no LineageWeave elapsed transport limit."""
    assert _validated_answer_timeout(None) is None
    assert _validated_answer_timeout("") is None
    assert _validated_answer_timeout("   ") is None
