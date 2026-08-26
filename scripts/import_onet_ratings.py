"""Validate and import one official O*NET occupation-rating CSV artifact."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg

_RATING_FIELDS = {
    "O*NET-SOC Code",
    "Title",
    "Element ID",
    "Element Name",
    "Scale ID",
    "Scale Name",
    "Data Value",
    "N",
    "Standard Error",
    "Lower CI Bound",
    "Upper CI Bound",
    "Recommend Suppress",
    "Date",
    "Domain Source",
}
_SCALE_FIELDS = {"Scale ID", "Scale Name", "Minimum", "Maximum"}
_SOURCE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_SCALES_SOURCE_CODE = "scales_reference"
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class ScaleDefinition:
    """One exact O*NET scale identity and its declared numeric bounds."""

    scale_id: str
    scale_name: str
    minimum_value: Decimal
    maximum_value: Decimal


@dataclass(frozen=True)
class RatingObservation:
    """One validated O*NET occupation-to-element source observation."""

    onetsoc_code: str
    occupation_title: str
    element_id: str
    element_name: str
    scale_id: str
    category_value: int | None
    data_value: Decimal
    sample_size: int | None
    standard_error: Decimal | None
    lower_ci_bound: Decimal | None
    upper_ci_bound: Decimal | None
    recommend_suppress: bool | None
    not_relevant: bool | None
    source_updated_date: date
    domain_source_code: str


def _decimal(value: str, field: str, *, optional: bool = False) -> Decimal | None:
    """Parse one finite source decimal while preserving an honest blank."""
    text = value.strip()
    if optional and not text:
        return None
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"invalid {field}: {value!r}")
    return parsed


def _integer(value: str, field: str, *, optional: bool = False) -> int | None:
    """Parse one source integer while preserving an honest blank."""
    text = value.strip()
    if optional and not text:
        return None
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc


def _flag(value: str, field: str) -> bool | None:
    """Parse the official Y/N/blank tri-state flag vocabulary."""
    text = value.strip()
    if not text:
        return None
    if text == "Y":
        return True
    if text == "N":
        return False
    raise ValueError(f"invalid {field} flag: {value!r}")


def _updated_month(value: str, today: date) -> date:
    """Parse O*NET MM/YYYY source dates and reject a future release month."""
    try:
        month_text, year_text = value.strip().split("/")
        parsed = date(int(year_text), int(month_text), 1)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid source update date: {value!r}") from exc
    if parsed > today.replace(day=1):
        raise ValueError(f"future source update date: {value!r}")
    return parsed


def _rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    """Read one UTF-8 CSV only when its authoritative columns are present."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"missing CSV columns: {', '.join(missing)}")
        return [dict(row) for row in reader]


def read_scale_file(path: Path) -> dict[str, ScaleDefinition]:
    """Return exact scale definitions from the official Scales Reference CSV."""
    scales: dict[str, ScaleDefinition] = {}
    for row in _rows(path, _SCALE_FIELDS):
        scale_id = row["Scale ID"].strip()
        definition = ScaleDefinition(
            scale_id=scale_id,
            scale_name=row["Scale Name"].strip(),
            minimum_value=_decimal(row["Minimum"], "scale minimum"),  # type: ignore[arg-type]
            maximum_value=_decimal(row["Maximum"], "scale maximum"),  # type: ignore[arg-type]
        )
        if not scale_id or not definition.scale_name:
            raise ValueError("empty scale identity")
        if definition.minimum_value > definition.maximum_value:
            raise ValueError(f"inverted scale bounds: {scale_id}")
        if scale_id in scales and scales[scale_id] != definition:
            raise ValueError(f"conflicting scale definition: {scale_id}")
        scales[scale_id] = definition
    if not scales:
        raise ValueError("scale file has no rows")
    return scales


def read_rating_file(
    path: Path,
    scales: dict[str, ScaleDefinition],
    *,
    today: date | None = None,
) -> list[RatingObservation]:
    """Validate an official rating CSV and return exact source observations."""
    observed_today = today or datetime.now(UTC).date()
    occupations: dict[str, str] = {}
    elements: dict[str, str] = {}
    observations: list[RatingObservation] = []
    identities: set[tuple[str, str, str, int | None]] = set()
    for row in _rows(path, _RATING_FIELDS):
        onetsoc_code = row["O*NET-SOC Code"].strip()
        occupation_title = row["Title"].strip()
        element_id = row["Element ID"].strip()
        element_name = row["Element Name"].strip()
        scale_id = row["Scale ID"].strip()
        scale = scales.get(scale_id)
        if scale is None or row["Scale Name"].strip() != scale.scale_name:
            raise ValueError(f"unknown or conflicting scale identity: {scale_id}")
        if (
            onetsoc_code in occupations
            and occupations[onetsoc_code] != occupation_title
        ):
            raise ValueError(f"conflicting occupation title: {onetsoc_code}")
        if element_id in elements and elements[element_id] != element_name:
            raise ValueError(f"conflicting element name: {element_id}")
        occupations[onetsoc_code] = occupation_title
        elements[element_id] = element_name
        data_value = _decimal(row["Data Value"], "data value")
        if not scale.minimum_value <= data_value <= scale.maximum_value:  # type: ignore[operator]
            raise ValueError(f"data value outside scale {scale_id}")
        sample_size = _integer(row["N"], "sample size", optional=True)
        standard_error = _decimal(
            row["Standard Error"], "standard error", optional=True
        )
        lower = _decimal(row["Lower CI Bound"], "lower CI bound", optional=True)
        upper = _decimal(row["Upper CI Bound"], "upper CI bound", optional=True)
        if sample_size is not None and sample_size <= 0:
            raise ValueError("sample size must be positive")
        if standard_error is not None and standard_error < 0:
            raise ValueError("standard error must be non-negative")
        if (lower is None) != (upper is None) or (lower is not None and lower > upper):
            raise ValueError("invalid confidence interval")
        category = _integer(row.get("Category", ""), "category", optional=True)
        identity = (onetsoc_code, element_id, scale_id, category)
        if identity in identities:
            raise ValueError(f"duplicate rating identity: {identity}")
        identities.add(identity)
        domain_source = row["Domain Source"].strip()
        if (
            not onetsoc_code
            or not occupation_title
            or not element_id
            or not element_name
            or not domain_source
        ):
            raise ValueError("empty rating identity")
        observations.append(
            RatingObservation(
                onetsoc_code=onetsoc_code,
                occupation_title=occupation_title,
                element_id=element_id,
                element_name=element_name,
                scale_id=scale_id,
                category_value=category,
                data_value=data_value,  # type: ignore[arg-type]
                sample_size=sample_size,
                standard_error=standard_error,
                lower_ci_bound=lower,
                upper_ci_bound=upper,
                recommend_suppress=_flag(
                    row["Recommend Suppress"], "recommend suppress"
                ),
                not_relevant=_flag(row.get("Not Relevant", ""), "not relevant"),
                source_updated_date=_updated_month(row["Date"], observed_today),
                domain_source_code=domain_source,
            )
        )
    if not observations:
        raise ValueError("rating file has no rows")
    return observations


def _parser() -> argparse.ArgumentParser:
    """Build the explicit, provenance-bearing importer command contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dsn", required=True)
    parser.add_argument("--release-code", required=True)
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--source-table-code", required=True)
    parser.add_argument("--source-table-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--source-row-count", type=int, required=True)
    parser.add_argument("--publisher", default="National Center for O*NET Development")
    parser.add_argument(
        "--license-url", default="https://creativecommons.org/licenses/by/4.0/"
    )
    parser.add_argument("--scales-file", type=Path, required=True)
    parser.add_argument("--scales-url", required=True)
    parser.add_argument("--scales-sha256", required=True)
    parser.add_argument("--scales-row-count", type=int, required=True)
    parser.add_argument("--ratings-file", type=Path, required=True)
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    """Reject ambiguous provenance and unsafe source identities before I/O."""
    if (
        not _SOURCE_CODE.fullmatch(args.source_table_code)
        or args.source_table_code == _SCALES_SOURCE_CODE
    ):
        raise ValueError("source table code must be non-reserved lower snake case")
    for field in ("release_code", "release_version", "source_table_name", "publisher"):
        if not str(getattr(args, field)).strip():
            raise ValueError(f"{field} must not be blank")
    for field in ("source_sha256", "scales_sha256"):
        if not _SHA256.fullmatch(str(getattr(args, field))):
            raise ValueError(f"{field} must be one SHA-256 digest")
    for field in ("source_row_count", "scales_row_count"):
        if getattr(args, field) <= 0:
            raise ValueError(f"{field} must be positive")
    for field in ("source_url", "scales_url", "license_url"):
        parsed = urlsplit(str(getattr(args, field)))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username:
            raise ValueError(f"{field} must be an HTTPS URL without userinfo")
    for field in ("ratings_file", "scales_file"):
        if not getattr(args, field).is_file():
            raise ValueError(f"{field} must be a regular file")


async def _reject_reference_conflicts(
    conn: asyncpg.Connection,
    args: argparse.Namespace,
    scales: dict[str, ScaleDefinition],
    observations: list[RatingObservation],
) -> None:
    """Reject a reused source identity whose immutable source labels differ."""
    release = await conn.fetchrow(
        """select release_version, source_publisher_name, source_license_url
             from occupational_data_release where data_release_code = $1""",
        args.release_code,
    )
    if release is not None and tuple(release) != (
        args.release_version,
        args.publisher,
        args.license_url,
    ):
        raise ValueError("conflicting release identity")
    sources = (
        (
            args.source_table_code,
            args.source_table_name,
            args.source_url,
            args.source_sha256.lower(),
            args.source_row_count,
        ),
        (
            _SCALES_SOURCE_CODE,
            "Scales Reference",
            args.scales_url,
            args.scales_sha256.lower(),
            args.scales_row_count,
        ),
    )
    for source_code, source_name, source_url, source_digest, source_rows in sources:
        source = await conn.fetchrow(
            """select source_table_name, source_artifact_url,
                      source_artifact_sha256, source_row_count
                 from occupational_source_table
                where data_release_code = $1 and source_table_code = $2""",
            args.release_code,
            source_code,
        )
        if source is not None and tuple(source) != (
            source_name,
            source_url,
            source_digest,
            source_rows,
        ):
            raise ValueError(f"conflicting source-table identity: {source_code}")
    expected = {
        "scale": {
            item.scale_id: (
                _SCALES_SOURCE_CODE,
                item.scale_name,
                item.minimum_value,
                item.maximum_value,
            )
            for item in scales.values()
        },
        "occupation": {
            item.onetsoc_code: (item.occupation_title,) for item in observations
        },
        "element": {item.element_id: (item.element_name,) for item in observations},
    }
    queries = {
        "scale": "select scale_id, source_table_code, scale_name, minimum_value, maximum_value from occupational_scale_definition where data_release_code = $1",
        "occupation": "select onetsoc_code, occupation_title from occupational_classification_entry where data_release_code = $1",
        "element": "select element_id, element_name from occupational_element_definition where data_release_code = $1",
    }
    for kind, query in queries.items():
        for row in await conn.fetch(query, args.release_code):
            source_id, *values = tuple(row)
            if (
                source_id in expected[kind]
                and tuple(values) != expected[kind][source_id]
            ):
                raise ValueError(f"conflicting {kind} identity: {source_id}")


async def import_ratings(args: argparse.Namespace) -> dict[str, object]:
    """Validate one pinned source artifact, then transactionally UPSERT its rows."""
    _validate_args(args)
    digest = hashlib.sha256(args.ratings_file.read_bytes()).hexdigest()
    if digest != args.source_sha256.lower():
        raise ValueError("rating artifact SHA-256 mismatch")
    scales_digest = hashlib.sha256(args.scales_file.read_bytes()).hexdigest()
    if scales_digest != args.scales_sha256.lower():
        raise ValueError("scales artifact SHA-256 mismatch")
    scales = read_scale_file(args.scales_file)
    if len(scales) != args.scales_row_count:
        raise ValueError("scales artifact row-count mismatch")
    observations = read_rating_file(args.ratings_file, scales)
    if len(observations) != args.source_row_count:
        raise ValueError("rating artifact row-count mismatch")
    conn = await asyncpg.connect(args.target_dsn)
    release_partition = f"occupational_rating_release_{hashlib.sha256(args.release_code.encode()).hexdigest()[:16]}"
    source_partition = f"occupational_rating_source_{hashlib.sha256(f'{args.release_code}\0{args.source_table_code}'.encode()).hexdigest()[:16]}"
    try:
        async with conn.transaction():
            await conn.execute(
                "select pg_advisory_xact_lock(hashtextextended($1, 0))",
                args.release_code,
            )
            await _reject_reference_conflicts(conn, args, scales, observations)
            release_literal = await conn.fetchval(
                "select quote_literal($1)", args.release_code
            )
            source_literal = await conn.fetchval(
                "select quote_literal($1)", args.source_table_code
            )
            await conn.execute(
                """insert into occupational_data_release
                       (data_release_code, release_version, source_publisher_name, source_license_url)
                   values ($1, $2, $3, $4)
                   on conflict (data_release_code) do nothing""",
                args.release_code,
                args.release_version,
                args.publisher,
                args.license_url,
            )
            await conn.execute(
                f"create table if not exists {release_partition} partition of occupational_rating_observation for values in ({release_literal}) partition by list (source_table_code)"
            )
            await conn.execute(
                f"create table if not exists {source_partition} partition of {release_partition} for values in ({source_literal})"
            )
            await conn.execute(
                """insert into occupational_source_table
                       (data_release_code, source_table_code, source_table_name,
                        source_artifact_url, source_artifact_sha256, source_row_count)
                   values ($1, $2, $3, $4, $5, $6)
                   on conflict (data_release_code, source_table_code) do nothing""",
                args.release_code,
                args.source_table_code,
                args.source_table_name,
                args.source_url,
                digest,
                len(observations),
            )
            await conn.execute(
                """insert into occupational_source_table
                       (data_release_code, source_table_code, source_table_name,
                        source_artifact_url, source_artifact_sha256, source_row_count)
                   values ($1, $2, 'Scales Reference', $3, $4, $5)
                   on conflict (data_release_code, source_table_code) do nothing""",
                args.release_code,
                _SCALES_SOURCE_CODE,
                args.scales_url,
                scales_digest,
                len(scales),
            )
            await conn.executemany(
                """insert into occupational_scale_definition
                       (data_release_code, source_table_code, scale_id, scale_name,
                        minimum_value, maximum_value)
                   values ($1, $2, $3, $4, $5, $6)
                   on conflict (data_release_code, scale_id) do nothing""",
                [
                    (
                        args.release_code,
                        _SCALES_SOURCE_CODE,
                        item.scale_id,
                        item.scale_name,
                        item.minimum_value,
                        item.maximum_value,
                    )
                    for item in scales.values()
                ],
            )
            await conn.executemany(
                """insert into occupational_classification_entry
                       (data_release_code, onetsoc_code, occupation_title)
                   values ($1, $2, $3) on conflict (data_release_code, onetsoc_code) do nothing""",
                [
                    (args.release_code, code, title)
                    for code, title in {
                        item.onetsoc_code: item.occupation_title
                        for item in observations
                    }.items()
                ],
            )
            await conn.executemany(
                """insert into occupational_element_definition
                       (data_release_code, element_id, element_name)
                   values ($1, $2, $3) on conflict (data_release_code, element_id) do nothing""",
                [
                    (args.release_code, code, name)
                    for code, name in {
                        item.element_id: item.element_name for item in observations
                    }.items()
                ],
            )
            await conn.executemany(
                """insert into occupational_rating_observation
                       (data_release_code, source_table_code, onetsoc_code, element_id,
                        scale_id, category_value, data_value, sample_size, standard_error,
                        lower_ci_bound, upper_ci_bound, recommend_suppress, not_relevant,
                        source_updated_date, domain_source_code)
                   values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                   on conflict on constraint occupational_rating_identity_key do nothing""",
                [
                    (
                        args.release_code,
                        args.source_table_code,
                        item.onetsoc_code,
                        item.element_id,
                        item.scale_id,
                        item.category_value,
                        item.data_value,
                        item.sample_size,
                        item.standard_error,
                        item.lower_ci_bound,
                        item.upper_ci_bound,
                        item.recommend_suppress,
                        item.not_relevant,
                        item.source_updated_date,
                        item.domain_source_code,
                    )
                    for item in observations
                ],
            )
    finally:
        await conn.close()
    return {
        "release_code": args.release_code,
        "source_table_code": args.source_table_code,
        "imported_rows": len(observations),
        "source_sha256": digest,
        "scales_sha256": scales_digest,
    }


def main() -> None:
    """Run the command-line importer and print aggregate, non-identifying evidence."""
    print(
        json.dumps(asyncio.run(import_ratings(_parser().parse_args())), sort_keys=True)
    )


if __name__ == "__main__":
    main()
