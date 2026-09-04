"""Fail-closed runtime type checks for the measurement policy boundary."""

from __future__ import annotations

import pytest

from lineageweave.measurement_policy import (
    DichotomousItemPolicy,
    DichotomousObservation,
    DichotomousObservationState,
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


def test_item_policy_rejects_non_string_transport_fields_explicitly() -> None:
    """Malformed transport values must fail at the item-policy boundary, not via ``.strip``."""
    with pytest.raises(TypeError, match="item policy fields must be strings"):
        DichotomousItemPolicy(
            item_id=17,  # type: ignore[arg-type]
            rubric_version="v1",
            not_supported_criterion="No supporting evidence",
            supported_criterion="Supporting evidence present",
        )


def test_instrument_policy_rejects_non_string_identity_explicitly() -> None:
    """Instrument identity is a governed string and must not rely on incidental ``.strip`` errors."""
    with pytest.raises(TypeError, match="instrument_id"):
        InstrumentMeasurementPolicy(
            instrument_id=17,  # type: ignore[arg-type]
            revision=1,
            lifecycle=InstrumentLifecycle.DRAFT,
            model_family=None,
            activation_evidence_ref=None,
        )


def test_instrument_policy_rejects_non_string_activation_reference_explicitly() -> None:
    """Activation evidence references must be parsed to text before entering product policy."""
    with pytest.raises(TypeError, match="activation_evidence_ref"):
        InstrumentMeasurementPolicy(
            instrument_id="importance-evidence",
            revision=1,
            lifecycle=InstrumentLifecycle.PUBLISHED,
            model_family=MeasurementModelFamily.IRT_2PLM,
            activation_evidence_ref=17,  # type: ignore[arg-type]
        )


def test_instrument_revision_rejects_boolean_transport_value_as_wrong_type() -> None:
    """JSON booleans are Python integers; they must not become instrument revisions."""
    with pytest.raises(TypeError, match="revision"):
        InstrumentMeasurementPolicy(
            instrument_id="importance-evidence",
            revision=True,  # type: ignore[arg-type]
            lifecycle=InstrumentLifecycle.DRAFT,
            model_family=None,
            activation_evidence_ref=None,
        )


def test_observed_response_rejects_boolean_transport_value_as_wrong_type() -> None:
    """A JSON boolean must not be accepted or classified as an ordinary invalid 0/1 score."""
    with pytest.raises(TypeError, match="response"):
        DichotomousObservation(DichotomousObservationState.OBSERVED, True)  # type: ignore[arg-type]


def test_unscored_response_rejects_non_integer_transport_value_as_wrong_type() -> None:
    """Malformed non-null response payloads fail at the type boundary before state semantics."""
    with pytest.raises(TypeError, match="response"):
        DichotomousObservation(DichotomousObservationState.MISSING, "0")  # type: ignore[arg-type]


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
