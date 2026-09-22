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
        if any(not isinstance(value, str) for value in values):
            raise TypeError("dichotomous item policy fields must be strings")
        if any(not value.strip() for value in values):
            raise ValueError("dichotomous item policy fields must be non-empty")
        for field_name, value in (
            ("item_id", self.item_id),
            ("rubric_version", self.rubric_version),
        ):
            if value != value.strip():
                raise ValueError(f"{field_name} must not contain surrounding whitespace")
        if self.not_supported_criterion.strip() == self.supported_criterion.strip():
            raise ValueError("0 and 1 rubric criteria must be distinct")


@dataclass(frozen=True, slots=True)
class InstrumentMeasurementPolicy:
    """Scoring activation contract for one immutable instrument revision.

    Draft and pilot instruments may preserve observations without a latent
    model. A published instrument must bind both a governed model family and an
    activation-evidence reference; otherwise operational latent scoring remains
    unavailable. Adapters must parse lifecycle and model-family strings into the
    governed enums before constructing this domain object; raw strings cannot
    bypass lifecycle-specific activation rules. Identity and evidence references
    likewise must be parsed to text before construction instead of relying on
    incidental string-method failures.
    """

    instrument_id: str
    revision: int
    lifecycle: InstrumentLifecycle
    model_family: MeasurementModelFamily | None
    activation_evidence_ref: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.lifecycle, InstrumentLifecycle):
            raise TypeError("lifecycle must be an InstrumentLifecycle")
        if self.model_family is not None and not isinstance(
            self.model_family, MeasurementModelFamily
        ):
            raise TypeError("model_family must be a MeasurementModelFamily when supplied")
        if not isinstance(self.instrument_id, str):
            raise TypeError("instrument_id must be a string")
        if not self.instrument_id.strip():
            raise ValueError("instrument_id must be non-empty")
        if self.instrument_id != self.instrument_id.strip():
            raise ValueError("instrument_id must not contain surrounding whitespace")
        if type(self.revision) is not int:
            raise TypeError("instrument revision must be an integer")
        if self.revision < 1:
            raise ValueError("instrument revision must be a positive integer")
        if self.activation_evidence_ref is not None:
            if not isinstance(self.activation_evidence_ref, str):
                raise TypeError("activation_evidence_ref must be a string when supplied")
            if not self.activation_evidence_ref.strip():
                raise ValueError("activation evidence reference must be non-empty when supplied")
            if self.activation_evidence_ref != self.activation_evidence_ref.strip():
                raise ValueError(
                    "activation_evidence_ref must not contain surrounding whitespace"
                )
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
    Adapters must parse the observation-state enum before construction so a raw
    string cannot silently enter the governed binary-response domain.
    """

    state: DichotomousObservationState
    response: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, DichotomousObservationState):
            raise TypeError("state must be a DichotomousObservationState")
        if self.response is not None and type(self.response) is not int:
            raise TypeError("response must be an integer or None")
        if self.state is DichotomousObservationState.OBSERVED:
            if self.response not in (0, 1):
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
