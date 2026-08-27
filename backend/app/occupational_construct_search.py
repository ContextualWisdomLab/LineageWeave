"""Search assertion-backed occupational constructs under ADR 0257."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL

SEARCHABLE_FAMILIES = frozenset(
    {"cognitive_ability", "work_style", "work_activity"}
)
MIN_QUERY_CHARS = 2
MAX_QUERY_CHARS = 80
DEFAULT_SEARCH_LIMIT = 20
HARD_SEARCH_LIMIT = 50
CANDIDATE_CONSTRUCT_LIMIT = 200
PER_CONSTRUCT_ROW_LIMIT = 200
CONSTRUCT_IRI_PREFIX = "https://data.onetcenter.org/element/"
WITHDRAWN_TRUTH_STATUSES = frozenset({"truth_rejected", "truth_superseded"})


class OccupationalConstructSearchError(ValueError):
    """Fail-closed catalog-search input or cursor."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class OccupationalConstructSearchHit:
    """One visible catalog match and the Post a reviewer should open next."""

    construct_id: str
    construct_iri: str
    construct_family_code: str
    preferred_label: str
    vocabulary_version: str
    supporting_post_id: str
    supporting_post_title: str
    evidence_text: str
    truth_status_code: str


@dataclass(frozen=True)
class OccupationalConstructSearchPage:
    """One keyset page of authorized catalog matches."""

    query: str
    family_code: str | None
    hits: tuple[OccupationalConstructSearchHit, ...]
    next_cursor: str | None


def like_contains_pattern(query: str) -> str:
    """Return a LIKE pattern that treats the query as a literal substring."""
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def normalize_construct_search_query(raw: str) -> str:
    """Trim and bound a catalog-search query or fail closed."""
    query = raw.strip()
    if len(query) < MIN_QUERY_CHARS:
        raise OccupationalConstructSearchError(
            "query_too_short",
            "Type two or more characters of a catalog label, then search.",
        )
    if len(query) > MAX_QUERY_CHARS:
        raise OccupationalConstructSearchError(
            "query_too_long",
            "Shorten the catalog label before searching.",
        )
    return query


def normalize_construct_search_family(raw: str | None) -> str | None:
    """Admit only synchronized O*NET construct families."""
    if raw is None or raw.strip() == "":
        return None
    family = raw.strip()
    if family not in SEARCHABLE_FAMILIES:
        raise OccupationalConstructSearchError(
            "unknown_family",
            "Search only cognitive ability, work style, or work activity.",
        )
    return family


def normalize_construct_search_cursor(raw: str | None) -> str | None:
    """Accept only an official O*NET element IRI as a keyset cursor."""
    if raw is None or raw.strip() == "":
        return None
    cursor = raw.strip()
    suffix = cursor.removeprefix(CONSTRUCT_IRI_PREFIX)
    if not cursor.startswith(CONSTRUCT_IRI_PREFIX) or not suffix or "/" in suffix:
        raise OccupationalConstructSearchError(
            "invalid_cursor",
            "Resume search from the last returned catalog IRI.",
        )
    return cursor


def normalize_construct_search_limit(raw: int | None) -> int:
    """Bound the visible page size without using OFFSET."""
    limit = DEFAULT_SEARCH_LIMIT if raw is None else raw
    if limit < 1 or limit > HARD_SEARCH_LIMIT:
        raise OccupationalConstructSearchError(
            "invalid_limit",
            f"Request between 1 and {HARD_SEARCH_LIMIT} catalog matches.",
        )
    return limit


def search_page_to_payload(page: OccupationalConstructSearchPage) -> dict[str, object]:
    """JSON object for GET /api/occupational-constructs/search."""
    return {
        "query": page.query,
        "family_code": page.family_code,
        "next_cursor": page.next_cursor,
        "hits": [
            {
                "construct_id": hit.construct_id,
                "construct_iri": hit.construct_iri,
                "construct_family_code": hit.construct_family_code,
                "preferred_label": hit.preferred_label,
                "vocabulary_version": hit.vocabulary_version,
                "supporting_post_id": hit.supporting_post_id,
                "supporting_post_title": hit.supporting_post_title,
                "evidence_text": hit.evidence_text,
                "truth_status_code": hit.truth_status_code,
            }
            for hit in page.hits
        ],
    }


def _row_mapping(row: Any) -> Mapping[str, Any]:
    """Accept asyncpg records and test dictionaries."""
    if isinstance(row, Mapping):
        return row
    return {key: row[key] for key in row.keys()}


def _collapse_visible_hits(
    rows: list[Any],
    can_see_post: Callable[[Any], bool],
    *,
    limit: int,
) -> tuple[list[OccupationalConstructSearchHit], bool]:
    """Keep one earliest visible Post per construct; drop conflicts and withdrawn truth."""
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    order: list[str] = []
    for row in rows:
        if not can_see_post(row):
            continue
        mapping = _row_mapping(row)
        construct_id = str(mapping["construct_id"])
        if construct_id not in grouped:
            grouped[construct_id] = []
            order.append(construct_id)
        grouped[construct_id].append(mapping)

    hits: list[OccupationalConstructSearchHit] = []
    for construct_id in order:
        visible_rows = grouped[construct_id]
        if int(visible_rows[0]["construct_row_count"]) > PER_CONSTRUCT_ROW_LIMIT:
            continue
        truth_statuses = {str(item["truth_status_code"]) for item in visible_rows}
        if len(truth_statuses) != 1:
            continue
        truth_status = next(iter(truth_statuses))
        if truth_status in WITHDRAWN_TRUTH_STATUSES:
            continue
        chosen = min(
            visible_rows,
            key=lambda item: (item["available_at"], str(item["post_id"])),
        )
        hits.append(
            OccupationalConstructSearchHit(
                construct_id=str(chosen["construct_id"]),
                construct_iri=str(chosen["construct_iri"]),
                construct_family_code=str(chosen["construct_family_code"]),
                preferred_label=str(chosen["preferred_label"]),
                vocabulary_version=str(chosen["version_label"]),
                supporting_post_id=str(chosen["post_id"]),
                supporting_post_title=str(chosen["post_title"]),
                evidence_text=str(chosen["evidence_text"]),
                truth_status_code=truth_status,
            )
        )
        if len(hits) == limit + 1:
            break
    truncated = len(hits) > limit
    return hits[:limit], truncated


async def search_visible_occupational_constructs(
    conn: Any,
    *,
    query: str,
    can_see_post: Callable[[Any], bool],
    family_code: str | None = None,
    knowledge_cutoff: datetime | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> OccupationalConstructSearchPage:
    """Return assertion-backed catalog matches the account may already read."""
    normalized_query = normalize_construct_search_query(query)
    normalized_family = normalize_construct_search_family(family_code)
    normalized_cursor = normalize_construct_search_cursor(cursor)
    page_size = normalize_construct_search_limit(limit)
    eligibility = SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")
    sql = """
        with matching_rows as (
            select construct.construct_id,
                   construct.construct_iri,
                   construct.construct_family_code,
                   construct.preferred_label,
                   vocabulary.version_label,
                   post.post_id,
                   post.post_title,
                   post.visibility_code,
                   post.corporate_entity_id,
                   post.process_unit_id,
                   assertion.evidence_text,
                   assertion.truth_status_code,
                   greatest(post.created_at, assertion.generated_at) as available_at,
                   dense_rank() over (order by construct.construct_iri) as construct_rank,
                   row_number() over (
                       partition by construct.construct_id
                       order by greatest(post.created_at, assertion.generated_at), post.post_id
                   ) as construct_row_number,
                   count(*) over (partition by construct.construct_id) as construct_row_count
              from occupational_construct construct
              join occupational_construct_vocabulary vocabulary
                on vocabulary.vocabulary_id = construct.vocabulary_id
              join post_occupational_construct_assertion assertion
                on assertion.construct_id = construct.construct_id
              join source_post post on post.post_id = assertion.post_id
              join post_occupational_construct_extraction extraction
                on extraction.post_id = assertion.post_id
              join post_content_ingestion_job job
                on job.post_id = assertion.post_id
               and job.source_body_sha256 = extraction.source_body_sha256
             where (
                    construct.preferred_label ilike $1 escape E'\\'
                    or coalesce(construct.construct_description, '') ilike $1 escape E'\\'
                   )
               and ($2::text is null or construct.construct_family_code = $2)
               and construct.construct_family_code in (
                    'cognitive_ability', 'work_style', 'work_activity'
               )
               and ($3::text is null or construct.construct_iri > $3)
               and {eligibility}
               and ($4::timestamptz is null
                    or greatest(post.created_at, assertion.generated_at) <= $4)
        )
        select * from matching_rows
         where construct_rank <= $5
           and construct_row_number <= $6
         order by construct_iri, available_at, post_id
            """.replace("{eligibility}", eligibility)
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        sql,
        like_contains_pattern(normalized_query),
        normalized_family,
        normalized_cursor,
        knowledge_cutoff,
        CANDIDATE_CONSTRUCT_LIMIT,
        PER_CONSTRUCT_ROW_LIMIT + 1,
    )
    hits, extra_visible = _collapse_visible_hits(rows, can_see_post, limit=page_size)
    candidate_constructs = {
        str(_row_mapping(row)["construct_iri"]) for row in rows
    }
    sql_exhausted = len(candidate_constructs) == CANDIDATE_CONSTRUCT_LIMIT
    next_cursor = None
    if extra_visible and hits:
        next_cursor = hits[-1].construct_iri
    elif sql_exhausted and rows:
        next_cursor = str(_row_mapping(rows[-1])["construct_iri"])
    return OccupationalConstructSearchPage(
        query=normalized_query,
        family_code=normalized_family,
        hits=tuple(hits),
        next_cursor=next_cursor,
    )


def occupational_construct_search_http_status(exc: OccupationalConstructSearchError) -> int:
    """Map search-input failures to HTTP 422."""
    del exc
    return 422


def occupational_construct_search_error_detail(exc: OccupationalConstructSearchError) -> str:
    """Return the buyer-facing search failure text."""
    return exc.detail
