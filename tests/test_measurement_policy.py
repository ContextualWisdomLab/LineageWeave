"""Contracts for LineageWeave-owned measurement policy, not numerical estimation."""

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


def test_production_model_families_keep_rasch_distinct_from_generic_1pl() -> None:
    """Public model identifiers expose the governed families and no generic 1PL."""
    assert {family.value for family in MeasurementModelFamily} == {
        "rasch",
        "irt_2plm",
        "irt_3plm",
        "irt_4plm",
    }


def test_observed_dichotomous_response_accepts_only_zero_or_one() -> None:
    """An observed criterion result is binary; missing-like states are not scores."""
    assert DichotomousObservation.observed(0).response == 0
    assert DichotomousObservation.observed(1).response == 1

    for invalid in (-1, 2):
        with pytest.raises(ValueError, match="0 or 1"):
            DichotomousObservation.observed(invalid)


def test_nonobserved_states_never_carry_a_binary_response() -> None:
    """Missing, abstain and adjudication states remain outside the 0/1 channel."""
    for state in (
        DichotomousObservationState.MISSING,
        DichotomousObservationState.NOT_OBSERVABLE,
        DichotomousObservationState.ABSTAIN,
        DichotomousObservationState.INVALID_EVIDENCE,
        DichotomousObservationState.ADJUDICATION_REQUIRED,
    ):
        observation = DichotomousObservation.unscored(state)
        assert observation.response is None
        assert observation.state is state

    with pytest.raises(ValueError, match="observed state"):
        DichotomousObservation.unscored(DichotomousObservationState.OBSERVED)


def test_item_policy_names_both_sides_of_the_binary_rubric() -> None:
    """Zero and one encode explicit rubric criteria instead of score compression."""
    policy = DichotomousItemPolicy(
        item_id="importance-evidence-1",
        rubric_version="2026-09-01",
        not_supported_criterion="Evidence does not establish the stated criterion.",
        supported_criterion="Evidence establishes the stated criterion.",
    )
    assert policy.not_supported_criterion != policy.supported_criterion

    with pytest.raises(ValueError, match="distinct"):
        DichotomousItemPolicy(
            item_id="importance-evidence-1",
            rubric_version="2026-09-01",
            not_supported_criterion="same",
            supported_criterion="same",
        )

    with pytest.raises(ValueError, match="non-empty"):
        DichotomousItemPolicy(" ", "v1", "not supported", "supported")


def test_pilot_instrument_may_preserve_observations_without_a_latent_model() -> None:
    """Pilot data are valid evidence even when no scoring model is defensible yet."""
    policy = InstrumentMeasurementPolicy(
        instrument_id="importance-evidence",
        revision=1,
        lifecycle=InstrumentLifecycle.PILOT,
        model_family=None,
        activation_evidence_ref=None,
    )
    assert policy.model_family is None


def test_published_instrument_requires_model_and_activation_evidence() -> None:
    """Operational scoring remains unavailable until model and evidence are bound."""
    with pytest.raises(ValueError, match="activation evidence"):
        InstrumentMeasurementPolicy(
            instrument_id="importance-evidence",
            revision=1,
            lifecycle=InstrumentLifecycle.PUBLISHED,
            model_family=MeasurementModelFamily.IRT_2PLM,
            activation_evidence_ref=None,
        )

    with pytest.raises(ValueError, match="model family"):
        InstrumentMeasurementPolicy(
            instrument_id="importance-evidence",
            revision=1,
            lifecycle=InstrumentLifecycle.PUBLISHED,
            model_family=None,
            activation_evidence_ref="evidence://pilot/2026-09",
        )

    policy = InstrumentMeasurementPolicy(
        instrument_id="importance-evidence",
        revision=1,
        lifecycle=InstrumentLifecycle.PUBLISHED,
        model_family=MeasurementModelFamily.IRT_2PLM,
        activation_evidence_ref="evidence://pilot/2026-09",
    )
    assert policy.lifecycle is InstrumentLifecycle.PUBLISHED


@pytest.mark.parametrize(
    ("instrument_id", "revision", "activation_evidence_ref", "message"),
    [
        (" ", 1, None, "instrument_id"),
        ("instrument", 0, None, "positive integer"),
        ("instrument", 1, " ", "non-empty"),
    ],
)
def test_instrument_identity_revision_and_evidence_are_bounded(
    instrument_id: str,
    revision: int,
    activation_evidence_ref: str | None,
    message: str,
) -> None:
    """Invalid identity, revision, and evidence values fail before activation."""
    with pytest.raises(ValueError, match=message):
        InstrumentMeasurementPolicy(
            instrument_id=instrument_id,
            revision=revision,
            lifecycle=InstrumentLifecycle.PILOT,
            model_family=None,
            activation_evidence_ref=activation_evidence_ref,
        )


def test_unscored_state_rejects_a_binary_payload_at_the_constructor_boundary() -> None:
    """Direct construction cannot bypass the unscored-state invariant."""
    with pytest.raises(ValueError, match="must not carry"):
        DichotomousObservation(DichotomousObservationState.MISSING, 0)
