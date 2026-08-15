"""Leakage-safe evidence contracts for direct-PostgreSQL analysis runs.

The public product must prove which immutable source snapshot and model
configuration produced a derived LineageWeave result without copying SQL,
DSNs, raw source text, image bytes, or private identifiers into logs or API
responses. This module owns that source-redacting contract. Persistence is
implemented by :mod:`backend.app.analysis_run_ingestion`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any, Mapping

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROFILE_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class AnalysisRunContractError(ValueError):
    """Raised when provenance evidence would be ambiguous or unsafe."""


def exact_text_sha256(value: str) -> str:
    """Return the SHA-256 of the exact UTF-8 text without normalization.

    Exact hashing is intentional: normalizing operator-supplied SQL or model
    configuration could make two semantically different source definitions
    appear identical.
    """

    if not isinstance(value, str):
        raise TypeError("value must be text")
    return sha256(value.encode("utf-8")).hexdigest()


def canonical_json_sha256(value: Mapping[str, Any]) -> str:
    """Hash a deterministic UTF-8 JSON representation of ``value``."""

    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _require_sha256(field_name: str, value: str) -> None:
    """Reject non-lowercase SHA-256 values with a content-redacting error."""

    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise AnalysisRunContractError(
            f"{field_name} must be a lowercase SHA-256 hex digest"
        )


def _require_nonempty(field_name: str, value: str, *, maximum: int = 255) -> None:
    """Require bounded, non-whitespace text without echoing private content."""

    if not isinstance(value, str) or not value.strip():
        raise AnalysisRunContractError(f"{field_name} must be non-empty text")
    if len(value) > maximum:
        raise AnalysisRunContractError(f"{field_name} exceeds {maximum} characters")


def _require_aware(field_name: str, value: datetime) -> None:
    """Require a timezone-aware timestamp so temporal comparisons are valid."""

    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise AnalysisRunContractError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True)
class SourceProfileReference:
    """Opaque reference to an operator-owned source query revision.

    ``profile_key`` is a non-sensitive deployment label. The query itself is
    never persisted by this contract; only its exact digest is retained.
    """

    profile_key: str
    profile_revision: int
    query_digest_sha256: str
    source_kind_code: str = "postgresql_query_profile"

    def __post_init__(self) -> None:
        """Validate the opaque identifier, immutable revision, and digest."""

        if not isinstance(self.profile_key, str) or _PROFILE_KEY_PATTERN.fullmatch(
            self.profile_key
        ) is None:
            raise AnalysisRunContractError(
                "profile_key must be a lowercase opaque identifier of at most "
                "128 characters"
            )
        if not isinstance(self.profile_revision, int) or isinstance(
            self.profile_revision, bool
        ):
            raise AnalysisRunContractError("profile_revision must be an integer")
        if self.profile_revision < 1:
            raise AnalysisRunContractError("profile_revision must be at least 1")
        _require_sha256("query_digest_sha256", self.query_digest_sha256)
        _require_nonempty("source_kind_code", self.source_kind_code, maximum=64)

    def public_json(self) -> dict[str, Any]:
        """Return the source-safe profile projection exposed to operators."""

        return {
            "profile_key": self.profile_key,
            "profile_revision": self.profile_revision,
            "query_digest_sha256": self.query_digest_sha256,
            "source_kind_code": self.source_kind_code,
        }


@dataclass(frozen=True)
class SourceSnapshotEvidence:
    """Aggregate-only evidence for one immutable source snapshot.

    ``maximum_available_time`` is the latest evidence-availability time in the
    snapshot. Requiring it not to exceed ``knowledge_cutoff`` prevents future
    information from entering a historical analysis run.
    """

    source_digest_sha256: str
    knowledge_cutoff: datetime
    maximum_available_time: datetime
    row_count: int
    document_count: int
    thread_count: int

    def __post_init__(self) -> None:
        """Validate digests, clocks, leakage boundary, and aggregate counts."""

        _require_sha256("source_digest_sha256", self.source_digest_sha256)
        _require_aware("knowledge_cutoff", self.knowledge_cutoff)
        _require_aware("maximum_available_time", self.maximum_available_time)
        if self.maximum_available_time > self.knowledge_cutoff:
            raise AnalysisRunContractError(
                "maximum_available_time must not exceed knowledge_cutoff"
            )
        for field_name in ("row_count", "document_count", "thread_count"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise AnalysisRunContractError(f"{field_name} must be an integer")
            if value < 0:
                raise AnalysisRunContractError(f"{field_name} must be non-negative")
        if self.document_count > self.row_count:
            raise AnalysisRunContractError(
                "document_count must not exceed row_count"
            )
        if self.thread_count > self.document_count:
            raise AnalysisRunContractError(
                "thread_count must not exceed document_count"
            )

    def public_json(self) -> dict[str, Any]:
        """Return aggregate evidence without source rows or identifiers."""

        return {
            "source_digest_sha256": self.source_digest_sha256,
            "knowledge_cutoff": self.knowledge_cutoff.isoformat(),
            "maximum_available_time": self.maximum_available_time.isoformat(),
            "row_count": self.row_count,
            "document_count": self.document_count,
            "thread_count": self.thread_count,
        }


@dataclass(frozen=True)
class AnalysisRunRegistration:
    """Actor, idempotency, and start time for one transactional run."""

    requested_by_account_id: str
    idempotency_key: str
    started_at: datetime

    def __post_init__(self) -> None:
        """Require bounded opaque identifiers and an aware start timestamp."""

        _require_nonempty(
            "requested_by_account_id", self.requested_by_account_id, maximum=128
        )
        _require_nonempty("idempotency_key", self.idempotency_key, maximum=255)
        _require_aware("started_at", self.started_at)


@dataclass(frozen=True)
class AnalysisRunConfiguration:
    """Versioned, bounded configuration that controls one analysis run."""

    row_limit: int
    write_reports: bool
    inspect_inline_images: bool
    validate_runtime_schema: bool
    model_contract_version: str
    output_profile: str

    def __post_init__(self) -> None:
        """Reject unbounded or ambiguous run configuration."""

        if not isinstance(self.row_limit, int) or isinstance(self.row_limit, bool):
            raise AnalysisRunContractError("row_limit must be an integer")
        if self.row_limit < 0:
            raise AnalysisRunContractError("row_limit must be non-negative")
        for field_name in (
            "write_reports",
            "inspect_inline_images",
            "validate_runtime_schema",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise AnalysisRunContractError(f"{field_name} must be a boolean")
        _require_nonempty(
            "model_contract_version", self.model_contract_version, maximum=128
        )
        _require_nonempty("output_profile", self.output_profile, maximum=128)

    def public_json(self) -> dict[str, Any]:
        """Return the bounded configuration safe for audit and API output."""

        return {
            "row_limit": self.row_limit,
            "write_reports": self.write_reports,
            "inspect_inline_images": self.inspect_inline_images,
            "validate_runtime_schema": self.validate_runtime_schema,
            "model_contract_version": self.model_contract_version,
            "output_profile": self.output_profile,
        }

    def request_digest(
        self,
        profile: SourceProfileReference,
        snapshot: SourceSnapshotEvidence,
    ) -> str:
        """Hash the complete source-safe request contract deterministically."""

        return canonical_json_sha256(
            {
                "source_profile": profile.public_json(),
                "source_snapshot": snapshot.public_json(),
                "configuration": self.public_json(),
            }
        )


@dataclass(frozen=True)
class AnalysisRunSummary:
    """Read-only, source-redacting operator projection for a persisted run."""

    analysis_run_id: str
    profile_key: str
    profile_revision: int
    run_status_code: str
    request_digest_sha256: str
    source_digest_sha256: str
    knowledge_cutoff: datetime
    maximum_available_time: datetime
    row_count: int
    document_count: int
    thread_count: int
    started_at: datetime
    completed_at: datetime | None
    configuration: AnalysisRunConfiguration

    def __post_init__(self) -> None:
        """Reuse evidence contracts and validate lifecycle timestamps."""

        _require_nonempty("analysis_run_id", self.analysis_run_id, maximum=128)
        _require_nonempty("profile_key", self.profile_key, maximum=128)
        if not isinstance(self.profile_revision, int) or isinstance(
            self.profile_revision, bool
        ):
            raise AnalysisRunContractError("profile_revision must be an integer")
        if self.profile_revision < 1:
            raise AnalysisRunContractError("profile_revision must be at least 1")
        _require_nonempty("run_status_code", self.run_status_code, maximum=64)
        _require_sha256("request_digest_sha256", self.request_digest_sha256)
        SourceSnapshotEvidence(
            source_digest_sha256=self.source_digest_sha256,
            knowledge_cutoff=self.knowledge_cutoff,
            maximum_available_time=self.maximum_available_time,
            row_count=self.row_count,
            document_count=self.document_count,
            thread_count=self.thread_count,
        )
        _require_aware("started_at", self.started_at)
        if self.completed_at is not None:
            _require_aware("completed_at", self.completed_at)
            if self.completed_at < self.started_at:
                raise AnalysisRunContractError(
                    "completed_at must not precede started_at"
                )

    def public_json(self) -> dict[str, Any]:
        """Return an API-safe summary with no DSN, SQL, raw content, or URI."""

        return {
            "analysis_run_id": self.analysis_run_id,
            "source_profile": {
                "profile_key": self.profile_key,
                "profile_revision": self.profile_revision,
            },
            "run_status_code": self.run_status_code,
            "request_digest_sha256": self.request_digest_sha256,
            "source_snapshot": {
                "source_digest_sha256": self.source_digest_sha256,
                "knowledge_cutoff": self.knowledge_cutoff.isoformat(),
                "maximum_available_time": self.maximum_available_time.isoformat(),
                "row_count": self.row_count,
                "document_count": self.document_count,
                "thread_count": self.thread_count,
            },
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "configuration": self.configuration.public_json(),
        }
