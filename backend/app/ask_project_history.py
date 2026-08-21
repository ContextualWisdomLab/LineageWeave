"""Authorization-safe project-history links for Ask responses.

The module accepts only citation identities already produced by post-scoped or
Global Ask. It re-applies current tenant visibility, source publication
eligibility, and the answer knowledge cutoff before returning citation labels or
project identities. A missing citation fails the whole persisted answer closed;
answer prose cannot be safely decomposed after one of its sources becomes
unauthorized.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.project_history import normalize_project_key

ASK_CITATION_LIMIT = 64
ASK_PROJECT_LIMIT = 8
GLOBAL_ASK_SESSION_CITATION_LIMIT = 256

_ELIGIBILITY = SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")
_CITATION_PROJECT_SQL = f"""
with visible_citation as materialized (
    select post.post_id::text as post_id,
           post.post_title,
           array_position($1::uuid[], post.post_id) as citation_ordinal,
           nullif(btrim(post.source_project_code), '') as source_project_code,
           nullif(btrim(post.source_project_name), '') as source_project_name
      from source_post post
     where post.post_id = any($1::uuid[])
       and (post.visibility_code = 'public'
            or post.corporate_entity_id::text = any($2::text[]))
       and post.created_at <= $3
       and {_ELIGIBILITY}
), project_evidence as (
    select visible_citation.post_id,
           coalesce(visible_citation.source_project_code,
                    visible_citation.source_project_name) as project_key,
           coalesce(visible_citation.source_project_name,
                    visible_citation.source_project_code) as project_name,
           'observed'::text as truth_status_code,
           0::integer as truth_order
      from visible_citation
     where coalesce(visible_citation.source_project_code,
                    visible_citation.source_project_name) is not null
    union all
    select visible_citation.post_id,
           coalesce(nullif(btrim(mention.project_key), ''),
                    nullif(btrim(mention.project_name), '')) as project_key,
           coalesce(nullif(btrim(mention.project_name), ''),
                    nullif(btrim(mention.project_key), '')) as project_name,
           'inferred'::text as truth_status_code,
           1::integer as truth_order
      from visible_citation
      join post_project_mention mention
        on mention.post_id::text = visible_citation.post_id
     where coalesce(nullif(btrim(mention.project_key), ''),
                    nullif(btrim(mention.project_name), '')) is not null
)
select visible_citation.post_id,
       visible_citation.post_title,
       visible_citation.citation_ordinal,
       project_evidence.project_key,
       project_evidence.project_name,
       project_evidence.truth_status_code,
       project_evidence.truth_order
  from visible_citation
  left join project_evidence
    on project_evidence.post_id = visible_citation.post_id
 order by visible_citation.citation_ordinal,
          project_evidence.truth_order nulls last,
          project_evidence.project_name nulls last,
          project_evidence.project_key nulls last
"""
_SESSION_CITATION_SQL = """
select distinct cited_post_id::text as cited_post_id
  from global_ask_turn_citation
 where global_ask_session_id = $1
 order by cited_post_id::text
 limit $2
"""


class AskEvidenceConnection(Protocol):
    """Minimal async query port used by this read projection."""

    async def fetch(self, query: str, *args: object) -> Sequence[Mapping[str, Any]]:
        """Execute a bounded read query."""

        raise NotImplementedError


@dataclass(frozen=True)
class AskEvidenceProjection:
    """Currently authorized citation labels and exact project links."""

    all_citations_visible: bool
    cited_posts: tuple[dict[str, str], ...]
    project_histories: tuple[dict[str, Any], ...]
    project_histories_truncated: bool
    knowledge_cutoff: str

    def response_fields(self) -> dict[str, Any]:
        """Return the public response fields shared by both Ask surfaces."""

        return {
            "cited_posts": list(self.cited_posts),
            "project_histories": list(self.project_histories),
            "project_histories_truncated": self.project_histories_truncated,
            "knowledge_cutoff": self.knowledge_cutoff,
        }


def ask_knowledge_cutoff(value: object | None = None) -> datetime:
    """Return an offset-aware UTC cutoff from a datetime or ISO text."""

    if value is None:
        return datetime.now(UTC)
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            normalized = value.strip()
            if normalized.endswith("Z"):
                normalized = f"{normalized[:-1]}+00:00"
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("knowledge cutoff must be ISO-8601") from exc
    else:
        raise ValueError("knowledge cutoff must be a datetime or ISO-8601 text")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("knowledge cutoff must include an offset")
    return parsed.astimezone(UTC)


def _cutoff_text(value: datetime) -> str:
    """Serialize one validated cutoff as canonical UTC RFC 3339 text."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _bounded_citations(
    cited_post_ids: Iterable[str], *, maximum_citations: int
) -> tuple[str, ...]:
    """Return unique citation IDs without silently truncating evidence."""

    try:
        citations = tuple(
            dict.fromkeys(
                str(UUID(str(value))) for value in cited_post_ids if str(value).strip()
            )
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("citation identities must be UUIDs") from exc
    if len(citations) > maximum_citations:
        raise ValueError("citation count exceeds the supported bound")
    return citations


async def read_authorized_ask_evidence(
    conn: AskEvidenceConnection,
    *,
    cited_post_ids: Iterable[str],
    corporate_entity_ids: Iterable[str],
    knowledge_cutoff: datetime | str,
    maximum_citations: int = ASK_CITATION_LIMIT,
    maximum_projects: int = ASK_PROJECT_LIMIT,
) -> AskEvidenceProjection:
    """Reauthorize citations and derive bounded exact-project history links.

    A citation is visible only when its current source row passes tenant ABAC,
    publication eligibility, and the answer cutoff. If any citation is absent,
    project links are withheld and callers must not reuse the persisted answer.
    """

    cutoff = ask_knowledge_cutoff(knowledge_cutoff)
    cutoff_text = _cutoff_text(cutoff)
    citations = _bounded_citations(
        cited_post_ids,
        maximum_citations=maximum_citations,
    )
    if not citations:
        return AskEvidenceProjection(True, (), (), False, cutoff_text)
    rows = list(
        await conn.fetch(
            _CITATION_PROJECT_SQL,
            list(citations),
            list(corporate_entity_ids),
            cutoff,
        )
    )
    citation_order = {post_id: index for index, post_id in enumerate(citations, start=1)}
    visible_titles: dict[str, str] = {}
    for row in rows:
        post_id = str(row["post_id"])
        if post_id in citation_order:
            visible_titles.setdefault(post_id, str(row["post_title"]))
    all_visible = set(visible_titles) == set(citations)
    cited_posts = tuple(
        {"post_id": post_id, "post_title": visible_titles[post_id]}
        for post_id in citations
        if post_id in visible_titles
    )
    if not all_visible:
        return AskEvidenceProjection(False, cited_posts, (), False, cutoff_text)

    evidence_rows = sorted(
        (
            row
            for row in rows
            if row.get("project_key") is not None and row.get("project_name") is not None
        ),
        key=lambda row: (
            citation_order[str(row["post_id"])],
            int(row.get("truth_order") or 0),
            str(row["project_name"]),
            str(row["project_key"]),
        ),
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in evidence_rows:
        project_key = str(row["project_key"]).strip()
        project_name = str(row["project_name"]).strip()
        try:
            normalized_key = normalize_project_key(project_key)
        except ValueError:
            continue
        post_id = str(row["post_id"])
        truth_order = int(row.get("truth_order") or 0)
        group = grouped.get(normalized_key)
        if group is None:
            grouped[normalized_key] = {
                "project_key": project_key,
                "project_name": project_name,
                "focus_post_id": post_id,
                "source_post_ids": [post_id],
                "knowledge_cutoff": cutoff_text,
                "truth_status_code": str(row["truth_status_code"]),
                "truth_order": truth_order,
                "first_citation_ordinal": citation_order[post_id],
            }
            continue
        if post_id not in group["source_post_ids"]:
            group["source_post_ids"].append(post_id)
        if truth_order < group["truth_order"]:
            group["project_key"] = project_key
            group["project_name"] = project_name
            group["truth_status_code"] = str(row["truth_status_code"])
            group["truth_order"] = truth_order

    ordered = sorted(
        grouped.values(),
        key=lambda group: (
            int(group["first_citation_ordinal"]),
            str(group["project_name"]),
            str(group["project_key"]),
        ),
    )
    truncated = len(ordered) > maximum_projects
    public_links: list[dict[str, Any]] = []
    for group in ordered[:maximum_projects]:
        public_links.append(
            {
                key: value
                for key, value in group.items()
                if key not in {"truth_order", "first_citation_ordinal"}
            }
        )
    return AskEvidenceProjection(
        True,
        cited_posts,
        tuple(public_links),
        truncated,
        cutoff_text,
    )


async def global_ask_session_citations_authorized(
    conn: AskEvidenceConnection,
    *,
    session_id: str,
    corporate_entity_ids: Iterable[str],
    knowledge_cutoff: datetime | str,
) -> bool:
    """Return whether every citation ever reused by a session is still visible."""

    rows = list(
        await conn.fetch(
            _SESSION_CITATION_SQL,
            session_id,
            GLOBAL_ASK_SESSION_CITATION_LIMIT + 1,
        )
    )
    if len(rows) > GLOBAL_ASK_SESSION_CITATION_LIMIT:
        return False
    citations = [str(row["cited_post_id"]) for row in rows]
    result = await read_authorized_ask_evidence(
        conn,
        cited_post_ids=citations,
        corporate_entity_ids=corporate_entity_ids,
        knowledge_cutoff=knowledge_cutoff,
        maximum_citations=GLOBAL_ASK_SESSION_CITATION_LIMIT,
        maximum_projects=0,
    )
    return result.all_citations_visible
