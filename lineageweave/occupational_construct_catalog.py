"""Synchronize an evidence-safe subset of the official O*NET catalog."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any


ONET_RELEASE = "31.0"
ONET_CONTENT_MODEL_URL = (
    "https://www.onetcenter.org/dl_files/database/"
    "db_31_0_json/content_model_reference.json"
)
ONET_CONTENT_MODEL_CANONICAL_SHA256 = (
    "cb25e83a25c355dba035afdfc6b23ed8706a939d5f5021ed772d554ea49afb06"
)
ONET_VOCABULARY_IRI = "https://www.onetcenter.org/database.html"
ONET_LICENSE_IRI = "https://creativecommons.org/licenses/by/4.0/"
ONET_ATTRIBUTION = (
    "This product includes information from the O*NET 31.0 Database by "
    "the U.S. Department of Labor, Employment and Training Administration "
    "(USDOL/ETA). Used under the CC BY 4.0 license. O*NET® is a trademark "
    "of USDOL/ETA."
)
_ELEMENT_ID = re.compile(r"^[0-9]+(?:\.[A-Za-z0-9]+)*$")
_FAMILY_ROOTS = (
    ("1.A.1", "cognitive_ability"),
    ("1.D", "work_style"),
    ("4.A", "work_activity"),
)


@dataclass(frozen=True)
class CatalogConstruct:
    """One exact O*NET Content Model element admitted by ADR 0250."""

    construct_iri: str
    family_code: str
    preferred_label: str
    description: str | None


def catalog_content_sha256(payload: dict[str, Any]) -> str:
    """Hash the deterministic canonical JSON representation of one release."""
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def parse_onet_construct_catalog(payload: dict[str, Any]) -> tuple[CatalogConstruct, ...]:
    """Parse only published cognitive, work-style, and work-activity roots."""
    if payload.get("table_id") != "content_model_reference":
        raise ValueError("O*NET payload is not the Content Model Reference")
    rows = payload.get("row")
    if not isinstance(rows, list):
        raise ValueError("O*NET Content Model Reference rows must be an array")

    constructs: dict[str, CatalogConstruct] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("O*NET Content Model Reference row must be an object")
        element_id = row.get("element_id")
        label = row.get("element_name")
        if not isinstance(element_id, str) or not _ELEMENT_ID.fullmatch(element_id):
            raise ValueError("O*NET element_id is malformed")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("O*NET element_name must be non-empty")
        if label != label.strip():
            raise ValueError("O*NET element_name must not contain outer whitespace")
        family = next(
            (
                family_code
                for root, family_code in _FAMILY_ROOTS
                if element_id == root or element_id.startswith(f"{root}.")
            ),
            None,
        )
        if family is None:
            continue
        description_value = row.get("description")
        if description_value is not None and not isinstance(description_value, str):
            raise ValueError("O*NET description must be text or null")
        description = (description_value or "").strip() or None
        iri = f"https://data.onetcenter.org/element/{element_id}"
        if iri in constructs:
            raise ValueError(f"duplicate O*NET construct IRI: {iri}")
        constructs[iri] = CatalogConstruct(iri, family, label, description)
    if not constructs:
        raise ValueError("O*NET catalog contains no governed construct roots")
    return tuple(constructs[iri] for iri in sorted(constructs))


async def sync_onet_construct_catalog(
    conn: Any,
    payload: dict[str, Any],
    *,
    expected_source_sha256: str = ONET_CONTENT_MODEL_CANONICAL_SHA256,
) -> int:
    """Atomically synchronize one immutable O*NET release and verify it exactly."""
    source_sha256 = catalog_content_sha256(payload)
    if source_sha256 != expected_source_sha256:
        raise ValueError("O*NET 31.0 source digest differs from the reviewed release")
    constructs = parse_onet_construct_catalog(payload)
    async with conn.transaction():
        vocabulary_id = await conn.fetchval(
            """
            insert into occupational_construct_vocabulary
                (vocabulary_iri, version_label, license_iri, attribution_text,
                 source_content_sha256)
            values ($1, $2, $3, $4, $5)
            on conflict (vocabulary_iri, version_label) do update set
                source_content_sha256 = coalesce(
                    occupational_construct_vocabulary.source_content_sha256,
                    excluded.source_content_sha256
                )
            where occupational_construct_vocabulary.license_iri = excluded.license_iri
              and occupational_construct_vocabulary.attribution_text = excluded.attribution_text
              and (
                  occupational_construct_vocabulary.source_content_sha256 is null
                  or occupational_construct_vocabulary.source_content_sha256 = excluded.source_content_sha256
              )
            returning vocabulary_id
            """,
            ONET_VOCABULARY_IRI,
            ONET_RELEASE,
            ONET_LICENSE_IRI,
            ONET_ATTRIBUTION,
            source_sha256,
        )
        if vocabulary_id is None:
            raise ValueError("O*NET release metadata conflicts with the stored catalog")
        await conn.executemany(
            """
            insert into occupational_construct
                (vocabulary_id, construct_iri, construct_family_code,
                 preferred_label, construct_description)
            values ($1, $2, $3, $4, $5)
            on conflict (vocabulary_id, construct_iri) do update set
                construct_description = coalesce(
                    occupational_construct.construct_description,
                    excluded.construct_description
                )
            where occupational_construct.construct_family_code = excluded.construct_family_code
              and occupational_construct.preferred_label = excluded.preferred_label
              and (
                  occupational_construct.construct_description is null
                  or occupational_construct.construct_description = excluded.construct_description
              )
            """,
            [
                (
                    vocabulary_id,
                    construct.construct_iri,
                    construct.family_code,
                    construct.preferred_label,
                    construct.description,
                )
                for construct in constructs
            ],
        )
        rows = await conn.fetch(
            """
            select construct_iri, construct_family_code, preferred_label,
                   construct_description
              from occupational_construct
             where vocabulary_id = $1
            """,
            vocabulary_id,
        )
        stored = {
            str(row["construct_iri"]): (
                str(row["construct_family_code"]),
                str(row["preferred_label"]),
                row["construct_description"],
            )
            for row in rows
        }
        expected = {
            construct.construct_iri: (
                construct.family_code,
                construct.preferred_label,
                construct.description,
            )
            for construct in constructs
        }
        if stored != expected:
            raise ValueError("stored O*NET catalog differs from the official release")
    return len(constructs)
