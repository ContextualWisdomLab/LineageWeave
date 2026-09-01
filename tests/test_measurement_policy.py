"""Contracts for LineageWeave-owned measurement policy, not numerical estimation."""

from __future__ import annotations

import pytest

from lineageweave.measurement_policy import (
    DichotomousObservation,
    DichotomousObservationState,
    MeasurementDomain,
    MeasurementModelFamily,
    default_dichotomous_model_family,
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

    for invalid in (-1, 2, True, False):
        with pytest.raises(ValueError, match="0 or 1"):
            DichotomousObservation.observed(invalid)  # type: ignore[arg-type]


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


def test_education_requires_an_explicit_rasch_or_guessing_mechanism() -> None:
    """Educational use never falls back silently to generic one-parameter IRT."""
    assert (
        default_dichotomous_model_family(
            MeasurementDomain.EDUCATIONAL,
            rasch_requirements_intended=True,
        )
        is MeasurementModelFamily.RASCH
    )
    assert (
        default_dichotomous_model_family(
            MeasurementDomain.EDUCATIONAL,
            lower_asymptote_justified=True,
        )
        is MeasurementModelFamily.IRT_3PLM
    )
    assert default_dichotomous_model_family(MeasurementDomain.EDUCATIONAL) is None


def test_psychology_defaults_to_2plm_when_discrimination_may_vary() -> None:
    """Psychology/SEM-lineage policy uses 2PLM as the default logistic family."""
    assert (
        default_dichotomous_model_family(MeasurementDomain.PSYCHOLOGY_SEM)
        is MeasurementModelFamily.IRT_2PLM
    )


def test_gambling_risk_requires_both_asymptote_mechanisms_for_4plm() -> None:
    """4PLM is selected only when lower and upper asymptotes are both justified."""
    assert (
        default_dichotomous_model_family(
            MeasurementDomain.GAMBLING_GAMING_RISK,
            lower_asymptote_justified=True,
            upper_asymptote_justified=True,
        )
        is MeasurementModelFamily.IRT_4PLM
    )
    assert (
        default_dichotomous_model_family(
            MeasurementDomain.GAMBLING_GAMING_RISK,
            lower_asymptote_justified=True,
        )
        is None
    )
