"""Canonical-text boundaries for LineageWeave-owned measurement policy."""

from __future__ import annotations

import pytest

from lineageweave.measurement_policy import (
    DichotomousItemPolicy,
    InstrumentLifecycle,
    InstrumentMeasurementPolicy,
)


@pytest.mark.parametrize("field_name", ["item_id", "rubric_version"])
def test_item_policy_rejects_surrounding_whitespace_in_identity_fields(
    field_name: str,
) -> None:
    """Opaque item and rubric identities must not acquire whitespace aliases."""
    values = {
        "item_id": "item-1",
        "rubric_version": "2026-09-01",
        "not_supported_criterion": "Evidence does not support the criterion.",
        "supported_criterion": "Evidence supports the criterion.",
    }
    values[field_name] = f" {values[field_name]} "

    with pytest.raises(ValueError, match="surrounding whitespace"):
        DichotomousItemPolicy(**values)


@pytest.mark.parametrize(
    ("instrument_id", "activation_evidence_ref"),
    [
        (" instrument-1 ", None),
        ("instrument-1", " evidence://pilot/2026-09 "),
    ],
)
def test_instrument_policy_rejects_surrounding_whitespace_in_canonical_refs(
    instrument_id: str,
    activation_evidence_ref: str | None,
) -> None:
    """Instrument and evidence references fail closed instead of forming aliases."""
    with pytest.raises(ValueError, match="surrounding whitespace"):
        InstrumentMeasurementPolicy(
            instrument_id=instrument_id,
            revision=1,
            lifecycle=InstrumentLifecycle.PILOT,
            model_family=None,
            activation_evidence_ref=activation_evidence_ref,
        )
