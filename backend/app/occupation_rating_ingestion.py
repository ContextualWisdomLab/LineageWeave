"""Read exact imported occupation ratings without deriving a score or weight."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol

OCCUPATION_CATALOG_BOUND = 2000


class RatingReadConnection(Protocol):
    """Small asyncpg-compatible surface used by the rating read projection."""

    async def fetchrow(self, query: str, *args: object) -> Any:
        """Return one row or ``None``."""

    async def fetch(self, query: str, *args: object) -> list[Any]:
        """Return ordered rows."""


def _decimal_text(value: Decimal | None) -> str | None:
    """Return the exact database decimal representation or honest absence."""
    return str(value) if value is not None else None


def _optional_mapping_value(row: Any, key: str) -> Any:
    """Return a mapping value when the projection supplied the column."""
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


async def fetch_occupation_ratings(
    conn: RatingReadConnection,
    *,
    data_release_code: str,
    source_table_code: str,
    onetsoc_code: str,
    limit: int,
    offset: int,
) -> dict[str, object]:
    """Return one bounded source profile and explicit artifact availability."""
    source = await conn.fetchrow(
        """select rating_source.source_table_name,
                  rating_source.source_artifact_url,
                  rating_source.source_artifact_sha256,
                  rating_source.source_row_count,
                  scale_source.source_artifact_url as scale_artifact_url,
                  scale_source.source_artifact_sha256 as scale_artifact_sha256,
                  scale_source.source_row_count as scale_source_row_count,
                  occupation.occupation_title
             from occupational_source_table rating_source
             left join occupational_source_table scale_source
               on scale_source.data_release_code = rating_source.data_release_code
              and scale_source.source_table_code = 'scales_reference'
             left join occupational_classification_entry occupation
               on occupation.data_release_code = rating_source.data_release_code
              and occupation.onetsoc_code = $3
            where rating_source.data_release_code = $1
              and rating_source.source_table_code = $2""",
        data_release_code,
        source_table_code,
        onetsoc_code,
    )
    if source is None:
        return {
            "data_release_code": data_release_code,
            "source_table_code": source_table_code,
            "onetsoc_code": onetsoc_code,
            "occupation_title": None,
            "source_available": False,
            "source": None,
            "items": [],
            "next_offset": None,
        }
    rows = await conn.fetch(
        """select observation.element_id, element.element_name,
                  observation.scale_id, scale.scale_name,
                  scale.minimum_value, scale.maximum_value,
                  observation.category_value, observation.data_value,
                  observation.sample_size, observation.standard_error,
                  observation.lower_ci_bound, observation.upper_ci_bound,
                  observation.recommend_suppress, observation.not_relevant,
                  observation.source_updated_month, observation.domain_source_code
             from occupational_rating_observation observation
             join occupational_element_definition element
               on element.data_release_code = observation.data_release_code
              and element.element_id = observation.element_id
             join occupational_scale_definition scale
               on scale.data_release_code = observation.data_release_code
              and scale.scale_id = observation.scale_id
            where observation.data_release_code = $1
              and observation.source_table_code = $2
              and observation.onetsoc_code = $3
            order by observation.element_id, observation.scale_id,
                     observation.category_value nulls first
            limit $4 offset $5""",
        data_release_code,
        source_table_code,
        onetsoc_code,
        limit + 1,
        offset,
    )
    page = rows[:limit]
    items = [
        {
            "element_id": row["element_id"],
            "element_name": row["element_name"],
            "scale_id": row["scale_id"],
            "scale_name": row["scale_name"],
            "minimum_value": _decimal_text(row["minimum_value"]),
            "maximum_value": _decimal_text(row["maximum_value"]),
            "category_value": row["category_value"],
            "data_value": _decimal_text(row["data_value"]),
            "sample_size": row["sample_size"],
            "standard_error": _decimal_text(row["standard_error"]),
            "lower_ci_bound": _decimal_text(row["lower_ci_bound"]),
            "upper_ci_bound": _decimal_text(row["upper_ci_bound"]),
            "recommend_suppress": row["recommend_suppress"],
            "not_relevant": row["not_relevant"],
            "source_updated_month": row["source_updated_month"],
            "domain_source_code": row["domain_source_code"],
        }
        for row in page
    ]
    return {
        "data_release_code": data_release_code,
        "source_table_code": source_table_code,
        "onetsoc_code": onetsoc_code,
        "occupation_title": _optional_mapping_value(source, "occupation_title"),
        "source_available": True,
        "source": {
            "source_table_name": source["source_table_name"],
            "source_artifact_url": source["source_artifact_url"],
            "source_artifact_sha256": source["source_artifact_sha256"],
            "source_row_count": source["source_row_count"],
            "scale_artifact_url": source["scale_artifact_url"],
            "scale_artifact_sha256": source["scale_artifact_sha256"],
            "scale_source_row_count": source["scale_source_row_count"],
        },
        "items": items,
        "next_offset": offset + limit if len(rows) > limit else None,
    }


async def fetch_occupation_rating_sources(
    conn: RatingReadConnection,
) -> dict[str, list[dict[str, object]]]:
    """Return imported rating artifacts that contain at least one observation."""
    rows = await conn.fetch(
        """select source.data_release_code, release.release_version,
                  release.source_publisher_name, release.source_license_url,
                  source.source_table_code, source.source_table_name,
                  source.source_artifact_url, source.source_artifact_sha256,
                  source.source_row_count
             from occupational_source_table source
             join occupational_data_release release
               on release.data_release_code = source.data_release_code
            where source.source_table_code <> 'scales_reference'
              and exists (
                    select 1
                      from occupational_rating_observation observation
                     where observation.data_release_code = source.data_release_code
                       and observation.source_table_code = source.source_table_code
              )
            order by release.imported_at desc, source.data_release_code,
                     source.source_table_name, source.source_table_code"""
    )
    return {"sources": [dict(row) for row in rows]}


async def fetch_occupation_rating_occupations(
    conn: RatingReadConnection,
    *,
    data_release_code: str,
    source_table_code: str,
) -> dict[str, object]:
    """Return occupations that have observations in one imported rating source."""
    source = await conn.fetchrow(
        """select source_table_code
             from occupational_source_table
            where data_release_code = $1
              and source_table_code = $2
              and source_table_code <> 'scales_reference'""",
        data_release_code,
        source_table_code,
    )
    if source is None:
        return {
            "data_release_code": data_release_code,
            "source_table_code": source_table_code,
            "source_available": False,
            "occupations": [],
        }
    rows = await conn.fetch(
        """select occupation.onetsoc_code, occupation.occupation_title
             from occupational_classification_entry occupation
            where occupation.data_release_code = $1
              and exists (
                    select 1
                      from occupational_rating_observation observation
                     where observation.data_release_code = occupation.data_release_code
                       and observation.source_table_code = $2
                       and observation.onetsoc_code = occupation.onetsoc_code
              )
            order by occupation.occupation_title, occupation.onetsoc_code
            limit $3""",
        data_release_code,
        source_table_code,
        OCCUPATION_CATALOG_BOUND,
    )
    return {
        "data_release_code": data_release_code,
        "source_table_code": source_table_code,
        "source_available": True,
        "occupations": [
            {
                "onetsoc_code": row["onetsoc_code"],
                "occupation_title": row["occupation_title"],
            }
            for row in rows
        ],
    }
