"""Fail-closed runtime type checks for the measurement policy boundary."""

from __future__ import annotations

import pytest

from lineageweave.measurement_policy import (
    DichotomousObservation,
    InstrumentLifecycle,
    InstrumentMeasurementPolicy,
    MeasurementModelFamily,
)


def test_string_lifecycle_cannot_bypass_published_activation_requirements() -> None:
    """A deserialized-looking string must not evade the published-state invariant."""
    with pytest.raises(TypeError, match="lifecycle"):
        InstrumentMeasurementPolicy(
            instrument_id="importance-evidence",
            revision=1,
            lifecycle="published",  # type: ignore[arg-type]
            model_family=None,
            activation_evidence_ref=None,
        )


def test_string_model_family_is_not_accepted_as_a_governed_family() -> None:
    """The domain object accepts only the versioned enum, not an unvalidated string."""
    with pytest.raises(TypeError, match="model_family"):
        InstrumentMeasurementPolicy(
            instrument_id="importance-evidence",
            revision=1,
            lifecycle=InstrumentLifecycle.PUBLISHED,
            model_family="irt_2plm",  # type: ignore[arg-type]
            activation_evidence_ref="evidence://pilot/2026-09",
        )


def test_string_observation_state_cannot_enter_the_binary_policy_domain() -> None:
    """Adapters must parse the governed state before constructing a domain observation."""
    with pytest.raises(TypeError, match="state"):
        DichotomousObservation("missing", None)  # type: ignore[arg-type]


def test_governed_enum_instances_still_construct_normally() -> None:
    """Runtime hardening must preserve the supported typed contract."""
    policy = InstrumentMeasurementPolicy(
        instrument_id="importance-evidence",
        revision=1,
        lifecycle=InstrumentLifecycle.PUBLISHED,
        model_family=MeasurementModelFamily.IRT_2PLM,
        activation_evidence_ref="evidence://pilot/2026-09",
    )
    assert policy.model_family is MeasurementModelFamily.IRT_2PLM
