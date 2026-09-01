"""Version-stable LineageWeave measurement-policy vocabulary.

This module owns product policy only. It deliberately contains no IRT fitting,
parameter estimation, judge routing, provider selection, or temporal analysis.
Those responsibilities stay with fast-mlsirm, contextual-orchestrator, and TEPP.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MeasurementModelFamily(StrEnum):
    """Production model families allowed by the current measurement policy.

    Rasch is intentionally a distinct family identifier. Generic one-parameter
    logistic IRT is not exposed as a normal production choice.
    """

    RASCH = "rasch"
    IRT_2PLM = "irt_2plm"
    IRT_3PLM = "irt_3plm"
    IRT_4PLM = "irt_4plm"


class MeasurementDomain(StrEnum):
    """Domain contexts that determine the default dichotomous model policy."""

    EDUCATIONAL = "educational"
    PSYCHOLOGY_SEM = "psychology_sem"
    GAMBLING_GAMING_RISK = "gambling_gaming_risk"


class DichotomousObservationState(StrEnum):
    """State of one rubric-governed dichotomous observation."""

    OBSERVED = "observed"
    MISSING = "missing"
    NOT_OBSERVABLE = "not_observable"
    ABSTAIN = "abstain"
    INVALID_EVIDENCE = "invalid_evidence"
    ADJUDICATION_REQUIRED = "adjudication_required"


@dataclass(frozen=True, slots=True)
class DichotomousObservation:
    """One 0/1 criterion observation or an explicitly unscored state.

    ``response=0`` means the versioned support criterion was not satisfied and
    ``response=1`` means it was satisfied. A response is never used to encode
    missingness, abstention, invalid evidence, or an unresolved adjudication.
    """

    state: DichotomousObservationState
    response: int | None

    def __post_init__(self) -> None:
        if self.state is DichotomousObservationState.OBSERVED:
            if type(self.response) is not int or self.response not in (0, 1):
                raise ValueError("observed dichotomous response must be integer 0 or 1")
            return
        if self.response is not None:
            raise ValueError("unscored dichotomous states must not carry a 0/1 response")

    @classmethod
    def observed(cls, response: int) -> "DichotomousObservation":
        """Create an observed 0/1 response under the instrument's rubric."""
        return cls(DichotomousObservationState.OBSERVED, response)

    @classmethod
    def unscored(
        cls,
        state: DichotomousObservationState,
    ) -> "DichotomousObservation":
        """Create a non-response state that remains outside the binary channel."""
        if state is DichotomousObservationState.OBSERVED:
            raise ValueError("observed state requires an explicit 0 or 1 response")
        return cls(state, None)


def default_dichotomous_model_family(
    domain: MeasurementDomain,
    *,
    rasch_requirements_intended: bool = False,
    lower_asymptote_justified: bool = False,
    upper_asymptote_justified: bool = False,
) -> MeasurementModelFamily | None:
    """Return the governed default family when its mechanism is explicit.

    ``None`` is a deliberate fail-closed result: the observations may be kept,
    but LineageWeave must not invent a latent score until a scientifically
    defensible model is selected and activated. This function selects policy;
    it performs no numerical psychometric computation.
    """
    if domain is MeasurementDomain.EDUCATIONAL:
        if rasch_requirements_intended:
            return MeasurementModelFamily.RASCH
        if lower_asymptote_justified and not upper_asymptote_justified:
            return MeasurementModelFamily.IRT_3PLM
        return None

    if domain is MeasurementDomain.PSYCHOLOGY_SEM:
        if rasch_requirements_intended or lower_asymptote_justified or upper_asymptote_justified:
            return None
        return MeasurementModelFamily.IRT_2PLM

    if domain is MeasurementDomain.GAMBLING_GAMING_RISK:
        if lower_asymptote_justified and upper_asymptote_justified:
            return MeasurementModelFamily.IRT_4PLM
        return None

    return None
