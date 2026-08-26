"""Persist evidence-bound occupational constructs under ADR 0249."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit


CONSTRUCT_FAMILIES = frozenset(
    {
        "cognitive_ability",
        "work_style",
        "work_activity",
        "affective_reaction",
        "performance_behavior",
    }
)
TRUTH_STATUS_CODES = frozenset(
    {
        "truth_authoritative",
        "truth_observed",
        "truth_inferred",
        "truth_proposed",
        "truth_superseded",
        "truth_rejected",
    }
)


def _https_iri(value: str, field_name: str) -> str:
    """Return one normalized HTTPS IRI or reject untrusted input."""
    normalized = value.strip()
    parsed = urlsplit(normalized)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{field_name} must be an absolute credential-free HTTPS IRI")
    return normalized


@dataclass(frozen=True)
class ConstructVocabulary:
    """One immutable external vocabulary release."""

    vocabulary_iri: str
    version_label: str
    license_iri: str
    attribution_text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "vocabulary_iri", _https_iri(self.vocabulary_iri, "vocabulary_iri"))
        object.__setattr__(self, "license_iri", _https_iri(self.license_iri, "license_iri"))
        if not self.version_label.strip() or not self.attribution_text.strip():
            raise ValueError("vocabulary version and attribution must be non-empty")


@dataclass(frozen=True)
class OccupationalConstruct:
    """One versioned external occupational construct."""

    vocabulary: ConstructVocabulary
    construct_iri: str
    family_code: str
    preferred_label: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "construct_iri", _https_iri(self.construct_iri, "construct_iri"))
        if self.family_code not in CONSTRUCT_FAMILIES:
            raise ValueError(f"unsupported occupational construct family {self.family_code!r}")
        if not self.preferred_label.strip():
            raise ValueError("construct preferred label must be non-empty")


@dataclass(frozen=True)
class OccupationalConstructAssertion:
    """One construct assertion bound to a verbatim semantic-unit span."""

    post_content_unit_id: str
    unit_text: str
    construct: OccupationalConstruct
    evidence_text: str
    truth_status_code: str
    extraction_method: str

    def __post_init__(self) -> None:
        for name, value in (
            ("post_content_unit_id", self.post_content_unit_id),
            ("unit_text", self.unit_text),
            ("evidence_text", self.evidence_text),
            ("truth_status_code", self.truth_status_code),
            ("extraction_method", self.extraction_method),
        ):
            if not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.evidence_text not in self.unit_text:
            raise ValueError("construct evidence must be a verbatim semantic-unit span")
        if self.truth_status_code not in TRUTH_STATUS_CODES:
            raise ValueError(f"unsupported ontology truth status {self.truth_status_code!r}")


async def persist_occupational_construct_assertions(
    conn: Any,
    post_id: str,
    orchestrator_session_id: str,
    assertions: tuple[OccupationalConstructAssertion, ...],
) -> None:
    """Atomically replace one Post's construct assertions and shared registry rows."""
    if not post_id.strip() or not orchestrator_session_id.strip():
        raise ValueError("post and orchestrator session identifiers must be non-empty")
    async with conn.transaction():
        await conn.execute(
            "delete from post_occupational_construct_assertion where post_id = $1",
            post_id,
        )
        for assertion in assertions:
            vocabulary = assertion.construct.vocabulary
            vocabulary_id = await conn.fetchval(
                """
                insert into occupational_construct_vocabulary
                    (vocabulary_iri, version_label, license_iri, attribution_text)
                values ($1, $2, $3, $4)
                on conflict (vocabulary_iri, version_label) do update set
                    vocabulary_iri = excluded.vocabulary_iri
                where occupational_construct_vocabulary.license_iri = excluded.license_iri
                  and occupational_construct_vocabulary.attribution_text = excluded.attribution_text
                returning vocabulary_id
                """,
                vocabulary.vocabulary_iri,
                vocabulary.version_label,
                vocabulary.license_iri,
                vocabulary.attribution_text,
            )
            if vocabulary_id is None:
                raise ValueError("vocabulary metadata conflicts with its immutable version")
            construct_id = await conn.fetchval(
                """
                insert into occupational_construct
                    (vocabulary_id, construct_iri, construct_family_code, preferred_label)
                values ($1, $2, $3, $4)
                on conflict (vocabulary_id, construct_iri) do update set
                    construct_iri = excluded.construct_iri
                where occupational_construct.construct_family_code = excluded.construct_family_code
                  and occupational_construct.preferred_label = excluded.preferred_label
                returning construct_id
                """,
                vocabulary_id,
                assertion.construct.construct_iri,
                assertion.construct.family_code,
                assertion.construct.preferred_label,
            )
            if construct_id is None:
                raise ValueError("construct metadata conflicts with its immutable vocabulary version")
            await conn.execute(
                """
                insert into post_occupational_construct_assertion
                    (post_id, post_content_unit_id, construct_id, evidence_text,
                     truth_status_code, extraction_method, orchestrator_session_id)
                values ($1, $2, $3, $4, $5, $6, $7)
                """,
                post_id,
                assertion.post_content_unit_id,
                construct_id,
                assertion.evidence_text,
                assertion.truth_status_code,
                assertion.extraction_method,
                orchestrator_session_id,
            )


async def load_occupational_construct_assertions(
    conn: Any, post_id: str
) -> list[dict[str, object]]:
    """Load assertions only after the caller has authorized their Post."""
    rows = await conn.fetch(
        """
        select construct.construct_iri, construct.construct_family_code,
               construct.preferred_label, vocabulary.vocabulary_iri,
               vocabulary.version_label, assertion.evidence_text,
               assertion.truth_status_code, assertion.extraction_method,
               assertion.generated_at, unit.unit_index
          from post_occupational_construct_assertion assertion
          join occupational_construct construct on construct.construct_id = assertion.construct_id
          join occupational_construct_vocabulary vocabulary
            on vocabulary.vocabulary_id = construct.vocabulary_id
          join post_content_unit unit
            on unit.post_content_unit_id = assertion.post_content_unit_id
         where assertion.post_id = $1
         order by unit.unit_index, construct.construct_family_code,
                  construct.preferred_label, construct.construct_iri
        """,
        post_id,
    )
    return [
        {
            "construct_iri": row["construct_iri"],
            "construct_family_code": row["construct_family_code"],
            "preferred_label": row["preferred_label"],
            "vocabulary_iri": row["vocabulary_iri"],
            "vocabulary_version": row["version_label"],
            "evidence_text": row["evidence_text"],
            "truth_status_code": row["truth_status_code"],
            "extraction_method": row["extraction_method"],
            "generated_at": row["generated_at"],
            "unit_index": row["unit_index"],
            "provenance": "post_occupational_construct_assertion.evidence_text",
        }
        for row in rows
    ]
