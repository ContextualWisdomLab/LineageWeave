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


class InstrumentLifecycle(StrEnum):
    """Governed lifecycle of a versioned measurement instrument."""

    DRAFT = "draft"
    PILOT = "pilot"
    PUBLISHED = "published"
    RETIRED = "retired"


class DichotomousObservationState(StrEnum):
    """State of one rubric-governed dichotomous observation."""

    OBSERVED = "observed"
    MISSING = "missing"
    NOT_OBSERVABLE = "not_observable"
    ABSTAIN = "abstain"
    INVALID_EVIDENCE = "invalid_evidence"
    ADJUDICATION_REQUIRED = "adjudication_required"


@dataclass(frozen=True, slots=True)
class DichotomousItemPolicy:
    """Versioned rubric that gives the binary response an explicit meaning."""

    item_id: str
    rubric_version: str
    not_supported_criterion: str
    supported_criterion: str

    def __post_init__(self) -> None:
        values = (
            self.item_id,
            self.rubric_version,
            self.not_supported_criterion,
            self.supported_criterion,
        )
        if any(not value.strip() for value in values):
            raise ValueError("dichotomous item policy fields must be non-empty")
        if self.not_supported_criterion.strip() == self.supported_criterion.strip():
            raise ValueError("0 and 1 rubric criteria must be distinct")


@dataclass(frozen=True, slots=True)
class InstrumentMeasurementPolicy:
    """Scoring activation contract for one immutable instrument revision.

    Draft and pilot instruments may preserve observations without a latent
    model. A published instrument must bind both a governed model family and an
    activation-evidence reference; otherwise operational latent scoring remains
    unavailable.
    """

    instrument_id: str
    revision: int
    lifecycle: InstrumentLifecycle
    model_family: MeasurementModelFamily | None
    activation_evidence_ref: str | None

    def __post_init__(self) -> None:
        if not self.instrument_id.strip():
            raise ValueError("instrument_id must be non-empty")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("instrument revision must be a positive integer")
        if self.activation_evidence_ref is not None and not self.activation_evidence_ref.strip():
            raise ValueError("activation evidence reference must be non-empty when supplied")
        if self.lifecycle is InstrumentLifecycle.PUBLISHED:
            if self.model_family is None:
                raise ValueError("published instrument requires a measurement model family")
            if self.activation_evidence_ref is None:
                raise ValueError("published instrument requires activation evidence")


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
            if lower_asymptote_justified or upper_asymptote_justified:
                return None
            return MeasurementModelFamily.RASCH
        if lower_asymptote_justified and not upper_asymptote_justified:
            return MeasurementModelFamily.IRT_3PLM
        return None

    if domain is MeasurementDomain.PSYCHOLOGY_SEM:
        if rasch_requirements_intended or lower_asymptote_justified or upper_asymptote_justified:
            return None
        return MeasurementModelFamily.IRT_2PLM

    if domain is MeasurementDomain.GAMBLING_GAMING_RISK:
        if rasch_requirements_intended:
            return None
        if lower_asymptote_justified and upper_asymptote_justified:
            return MeasurementModelFamily.IRT_4PLM
        return None

    return None
