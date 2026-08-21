"""Apply authorization-safe project-history links to both Ask surfaces."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    """Replace one exact source fragment and fail when branch context drifted."""

    file_path = ROOT / path
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor in {path}, found {count}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_new(path: str, content: str) -> None:
    """Create one product file and reject accidental overwrite."""

    file_path = ROOT / path
    if file_path.exists():
        raise RuntimeError(f"refusing to overwrite existing {path}")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content.strip() + "\n", encoding="utf-8")


def append_once(path: str, marker: str, content: str) -> None:
    """Append a documented section only when it is not already present."""

    file_path = ROOT / path
    text = file_path.read_text(encoding="utf-8")
    if marker in text:
        return
    file_path.write_text(text.rstrip() + "\n\n" + content.strip() + "\n", encoding="utf-8")


def create_backend_projection() -> None:
    """Create the authorization-first citation-to-project projection."""

    write_new(
        "backend/app/ask_project_history.py",
        r'''
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
from datetime import datetime, timezone
from typing import Any, Protocol

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
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("knowledge cutoff must be ISO-8601") from exc
    else:
        raise ValueError("knowledge cutoff must be a datetime or ISO-8601 text")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("knowledge cutoff must include an offset")
    return parsed.astimezone(timezone.utc)


def _cutoff_text(value: datetime) -> str:
    """Serialize one validated cutoff as canonical UTC RFC 3339 text."""

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded_citations(
    cited_post_ids: Iterable[str], *, maximum_citations: int
) -> tuple[str, ...]:
    """Return unique citation IDs without silently truncating evidence."""

    citations = tuple(dict.fromkeys(str(value) for value in cited_post_ids if str(value)))
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
''',
    )


def patch_post_chat_ingestion() -> None:
    """Apply cutoff and publication eligibility to both Ask retrieval paths."""

    replace_once(
        "backend/app/post_chat_ingestion.py",
        "from dataclasses import dataclass\nfrom typing import Any, Callable, Iterable\n",
        "from dataclasses import dataclass\nfrom datetime import datetime, timezone\n"
        "from typing import Any, Callable, Iterable\n",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        "from .knowledge_graph import hydrate_related_nodes, load_visible_subgraph\n",
        "from .knowledge_graph import hydrate_related_nodes, load_visible_subgraph\n"
        "from .post_eligibility import SOURCE_POST_ELIGIBILITY_SQL\n",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        "_POST_CHAT_SOURCE_LIMIT = 8\n_POST_CHAT_CANDIDATE_LIMIT = 32\n",
        "_POST_CHAT_SOURCE_LIMIT = 8\n_POST_CHAT_CANDIDATE_LIMIT = 32\n"
        "_SOURCE_ELIGIBILITY = SOURCE_POST_ELIGIBILITY_SQL.format(alias=\"source_post\")\n\n\n"
        "def _ask_cutoff(value: datetime | None) -> datetime:\n"
        "    \"\"\"Return an aware UTC cutoff for one Ask retrieval.\"\"\"\n\n"
        "    cutoff = value or datetime.now(timezone.utc)\n"
        "    if cutoff.tzinfo is None or cutoff.utcoffset() is None:\n"
        "        raise ValueError(\"knowledge_cutoff must include an offset\")\n"
        "    return cutoff.astimezone(timezone.utc)\n",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """async def gather_chat_sources(
    conn: asyncpg.Connection,
    post_id: str,
    can_see_post: Callable[[asyncpg.Record], bool],
    vision_client: ImageContentClient | None = None,
) -> list[ChatSourceDocument]:
""",
        """async def gather_chat_sources(
    conn: asyncpg.Connection,
    post_id: str,
    can_see_post: Callable[[asyncpg.Record], bool],
    vision_client: ImageContentClient | None = None,
    *,
    knowledge_cutoff: datetime | None = None,
) -> list[ChatSourceDocument]:
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """    if vision_client is None:
        vision_client = NullImageContentClient()

    this_post = await conn.fetchrow(
        "select post_id, post_title, post_body, source_system_code, source_record_key, "
""",
        """    if vision_client is None:
        vision_client = NullImageContentClient()
    cutoff = _ask_cutoff(knowledge_cutoff)

    this_post = await conn.fetchrow(
        "select post_id, post_title, post_body, created_at, source_system_code, source_record_key, "
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        '        "source_project_name from source_post where post_id = $1",\n        post_id,\n',
        '        f"source_project_name from source_post where post_id = $1 "\n'
        '        f"and created_at <= $2 and {_SOURCE_ELIGIBILITY}",\n'
        '        post_id,\n        cutoff,\n',
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        '        "source_project_code, source_project_name "\n'
        '        "from source_post where post_id = any($1::uuid[]) "\n'
        '        "order by array_position($1::uuid[], post_id) limit $2",\n'
        '        candidate_ids,\n        _POST_CHAT_CANDIDATE_LIMIT,\n',
        '        "source_project_code, source_project_name, created_at "\n'
        '        f"from source_post where post_id = any($1::uuid[]) "\n'
        '        f"and created_at <= $3 and {_SOURCE_ELIGIBILITY} "\n'
        '        "order by array_position($1::uuid[], post_id) limit $2",\n'
        '        candidate_ids,\n        _POST_CHAT_CANDIDATE_LIMIT,\n        cutoff,\n',
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """    question: str | None = None,
    limit: int = 4,
) -> list[ChatSourceDocument]:
""",
        """    question: str | None = None,
    limit: int = 4,
    knowledge_cutoff: datetime | None = None,
) -> list[ChatSourceDocument]:
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """    if vision_client is None:
        vision_client = NullImageContentClient()
    search_terms = tuple(
""",
        """    if vision_client is None:
        vision_client = NullImageContentClient()
    cutoff = _ask_cutoff(knowledge_cutoff)
    authorized_entity_ids = list(authorized_corporate_entity_ids)
    search_terms = tuple(
""",
    )
    eligibility = "{_SOURCE_ELIGIBILITY}"
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """                   (select post_id, created_at, 'title' as matched_in
                      from source_post
                     where post_title ilike '%' || $1 || '%'
                     limit 32)
""",
        f"""                   (select post_id, created_at, 'title' as matched_in
                      from source_post
                     where (visibility_code = 'public'
                            or corporate_entity_id::text = any($2::text[]))
                       and created_at <= $3
                       and {eligibility}
                       and post_title ilike '%' || $1 || '%'
                     limit 32)
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """                   (select post_id, created_at, 'body' as matched_in
                      from source_post
                     where lower(left(source_post_search_text(post_body), 16384))
                               like '%' || lower($1) || '%'
                     limit 32)
""",
        f"""                   (select post_id, created_at, 'body' as matched_in
                      from source_post
                     where (visibility_code = 'public'
                            or corporate_entity_id::text = any($2::text[]))
                       and created_at <= $3
                       and {eligibility}
                       and lower(left(source_post_search_text(post_body), 16384))
                               like '%' || lower($1) || '%'
                     limit 32)
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """                   (select post_id, created_at, 'body' as matched_in
                      from source_post
                     where to_tsvector('simple', source_post_search_text(post_body))
                               @@ plainto_tsquery('simple', $1)
                     limit 32)
""",
        f"""                   (select post_id, created_at, 'body' as matched_in
                      from source_post
                     where (visibility_code = 'public'
                            or corporate_entity_id::text = any($2::text[]))
                       and created_at <= $3
                       and {eligibility}
                       and to_tsvector('simple', source_post_search_text(post_body))
                               @@ plainto_tsquery('simple', $1)
                     limit 32)
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """                   (select post_id, created_at, 'source_field' as matched_in
                      from source_post
                     where concat_ws(' ', source_system_code, source_record_key,
""",
        f"""                   (select post_id, created_at, 'source_field' as matched_in
                      from source_post
                     where (visibility_code = 'public'
                            or corporate_entity_id::text = any($2::text[]))
                       and created_at <= $3
                       and {eligibility}
                       and concat_ws(' ', source_system_code, source_record_key,
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """            term,
        )
""",
        """            term,
            authorized_entity_ids,
            cutoff,
        )
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """         where visibility_code = 'public'
            or corporate_entity_id::text = any($1::text[])
         order by array_position($2::uuid[], post_id) nulls last,
                  created_at desc, post_id desc
         limit $3
        """,
        list(authorized_corporate_entity_ids),
        candidate_ids,
        limit,
""",
        f"""         where (visibility_code = 'public'
            or corporate_entity_id::text = any($1::text[]))
           and created_at <= $4
           and {eligibility}
         order by array_position($2::uuid[], post_id) nulls last,
                  created_at desc, post_id desc
         limit $3
        """,
        authorized_entity_ids,
        candidate_ids,
        limit,
        cutoff,
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        '        "select question_text, answer_text from post_chat_result "\n',
        '        "select question_text, answer_text, computed_at from post_chat_result "\n',
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        '        "cited_posts": [\n',
        '        "_knowledge_cutoff": header.get("computed_at"),\n        "cited_posts": [\n',
    )


def patch_main_routes() -> None:
    """Attach the reauthorized project links to stored and live Ask responses."""

    replace_once(
        "backend/app/main.py",
        "from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL\n",
        "from backend.app.ask_project_history import (\n"
        "    ask_knowledge_cutoff,\n"
        "    global_ask_session_citations_authorized,\n"
        "    read_authorized_ask_evidence,\n"
        ")\n"
        "from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL\n",
    )
    old_read = '''    await _load_visible_post(post_id, account, pool)
    async with pool.acquire() as conn:
        exchanges = await fetch_persisted_chats(conn, post_id)
    return {"post_id": post_id, "exchanges": exchanges}
'''
    new_read = '''    await _load_visible_post(post_id, account, pool)
    authorized_exchanges: list[dict[str, Any]] = []
    async with pool.acquire() as conn:
        exchanges = await fetch_persisted_chats(conn, post_id)
        for exchange in exchanges:
            cutoff = ask_knowledge_cutoff(exchange.get("_knowledge_cutoff"))
            evidence = await read_authorized_ask_evidence(
                conn,
                cited_post_ids=exchange["cited_post_ids"],
                corporate_entity_ids=account.corporate_entity_ids,
                knowledge_cutoff=cutoff,
            )
            if not evidence.all_citations_visible:
                continue
            public_exchange = {
                key: value for key, value in exchange.items() if not key.startswith("_")
            }
            public_exchange.update(evidence.response_fields())
            authorized_exchanges.append(public_exchange)
    return {"post_id": post_id, "exchanges": authorized_exchanges}
'''
    replace_once("backend/app/main.py", old_read, new_read)
    replace_once(
        "backend/app/main.py",
        """    post = await _load_visible_post(post_id, account, pool)
    post_metadata = build_post_llm_metadata(post_id, post)
    async with pool.acquire() as conn:
        stored = await fetch_persisted_chat(conn, post_id, question)
        if stored is not None:
            source_ids = [post_id]
            source_ids.extend(cid for cid in stored["cited_post_ids"] if cid != post_id)
            return {
                "post_id": post_id,
                "answer_text": stored["answer_text"],
                "cited_post_ids": stored["cited_post_ids"],
                "cited_posts": stored["cited_posts"],
                "source_post_ids": source_ids,
            }
        with use_llm_metadata(post_metadata):
""",
        """    post = await _load_visible_post(post_id, account, pool)
    post_metadata = build_post_llm_metadata(post_id, post)
    knowledge_cutoff = ask_knowledge_cutoff()
    async with pool.acquire() as conn:
        stored = await fetch_persisted_chat(conn, post_id, question)
        if stored is not None:
            stored_cutoff = ask_knowledge_cutoff(stored.get("_knowledge_cutoff"))
            stored_evidence = await read_authorized_ask_evidence(
                conn,
                cited_post_ids=stored["cited_post_ids"],
                corporate_entity_ids=account.corporate_entity_ids,
                knowledge_cutoff=stored_cutoff,
            )
            if stored_evidence.all_citations_visible:
                source_ids = list(
                    dict.fromkeys([post_id, *stored["cited_post_ids"]])
                )
                return {
                    "post_id": post_id,
                    "answer_text": stored["answer_text"],
                    "cited_post_ids": stored["cited_post_ids"],
                    "source_post_ids": source_ids,
                    **stored_evidence.response_fields(),
                }
        with use_llm_metadata(post_metadata):
""",
    )
    replace_once(
        "backend/app/main.py",
        """            sources = await gather_chat_sources(
                conn, post_id, lambda row: _can_see_post(account, row), vision_client=_vision_client()
            )
""",
        """            sources = await gather_chat_sources(
                conn,
                post_id,
                lambda row: _can_see_post(account, row),
                vision_client=_vision_client(),
                knowledge_cutoff=knowledge_cutoff,
            )
""",
    )
    replace_once(
        "backend/app/main.py",
        """    async with pool.acquire() as conn:
        await persist_post_chat(conn, post_id, question, answer.answer_text, cited_ids)
""",
        """    async with pool.acquire() as conn:
        await persist_post_chat(conn, post_id, question, answer.answer_text, cited_ids)
        answer_evidence = await read_authorized_ask_evidence(
            conn,
            cited_post_ids=cited_ids,
            corporate_entity_ids=account.corporate_entity_ids,
            knowledge_cutoff=knowledge_cutoff,
        )
    if not answer_evidence.all_citations_visible:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Post chat evidence changed before the answer could be returned",
        )
""",
    )
    replace_once(
        "backend/app/main.py",
        '        "cited_posts": cited_post_summaries(sources, cited_ids),\n'
        '        "source_post_ids": [source.post_id for source in sources],\n',
        '        "source_post_ids": [source.post_id for source in sources],\n'
        '        **answer_evidence.response_fields(),\n',
    )
    replace_once(
        "backend/app/main.py",
        """    client = _post_chat_client()
    if not client.available:
""",
        """    knowledge_cutoff = ask_knowledge_cutoff()
    client = _post_chat_client()
    if not client.available:
""",
    )
    replace_once(
        "backend/app/main.py",
        """        conversation = await load_global_ask_context(conn, session_id)
        sources = await gather_global_chat_sources(
""",
        """        if not await global_ask_session_citations_authorized(
            conn,
            session_id=session_id,
            corporate_entity_ids=account.corporate_entity_ids,
            knowledge_cutoff=knowledge_cutoff,
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Global Ask session evidence is no longer authorized; start a new session",
            )
        conversation = await load_global_ask_context(conn, session_id)
        sources = await gather_global_chat_sources(
""",
    )
    replace_once(
        "backend/app/main.py",
        """            question=question,
        )
""",
        """            question=question,
            knowledge_cutoff=knowledge_cutoff,
        )
""",
    )
    replace_once(
        "backend/app/main.py",
        '            "timeline": [],\n            "next_action": "No authorized source posts are available for this question.",\n',
        '            "timeline": [],\n            "project_histories": [],\n'
        '            "project_histories_truncated": False,\n'
        '            "knowledge_cutoff": knowledge_cutoff.isoformat().replace("+00:00", "Z"),\n'
        '            "next_action": "No authorized source posts are available for this question.",\n',
    )
    replace_once(
        "backend/app/main.py",
        """    async with pool.acquire() as conn:
        await persist_global_ask_turn(
            conn,
            conversation.session_id,
            question,
            answer.answer_text,
            cited_ids,
        )
""",
        """    async with pool.acquire() as conn:
        await persist_global_ask_turn(
            conn,
            conversation.session_id,
            question,
            answer.answer_text,
            cited_ids,
        )
        answer_evidence = await read_authorized_ask_evidence(
            conn,
            cited_post_ids=cited_ids,
            corporate_entity_ids=account.corporate_entity_ids,
            knowledge_cutoff=knowledge_cutoff,
        )
    if not answer_evidence.all_citations_visible:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Global Ask evidence changed before the answer could be returned",
        )
""",
    )
    replace_once(
        "backend/app/main.py",
        '        "cited_posts": cited_post_summaries(sources, cited_ids),\n'
        '        "cited_post_evidence": cited_post_evidence(sources, cited_ids),\n',
        '        "cited_post_evidence": cited_post_evidence(sources, cited_ids),\n',
    )
    replace_once(
        "backend/app/main.py",
        '        "timeline": global_ask_timeline(sources),\n    }\n',
        '        "timeline": global_ask_timeline(sources),\n'
        '        **answer_evidence.response_fields(),\n    }\n',
    )


def create_frontend_component() -> None:
    """Create one lazy canonical-timeline disclosure reused by both Ask surfaces."""

    write_new(
        "frontend/src/components/AskProjectHistoryLinks.tsx",
        r'''
import { useEffect, useId, useState } from "react";

import { fetchProjectHistory, type ProjectHistoryLink } from "../api";
import type { Locale } from "../i18n";
import { useLocale } from "../i18n";
import { projectHistoryText, type ProjectHistoryProjection } from "../projectHistory";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";
import "./AskProjectHistoryLinks.css";

interface Copy {
  heading: string;
  boundary: string;
  open: (name: string) => string;
  close: (name: string) => string;
  loading: string;
  truncated: string;
  observed: string;
  inferred: string;
}

const COPY: Record<Locale, Copy> = {
  en: {
    heading: "Project histories cited by this answer",
    boundary: "Each timeline is rebuilt from currently authorized evidence at the answer cutoff.",
    open: (name) => `Open project history: ${name}`,
    close: (name) => `Close project history: ${name}`,
    loading: "Loading cited project history...",
    truncated: "Additional cited projects are not shown. Open the cited source records to inspect their project evidence.",
    observed: "Observed project identity",
    inferred: "Inferred project identity",
  },
  ko: {
    heading: "이 답변이 인용한 프로젝트 이력",
    boundary: "각 타임라인은 답변 기준 시각과 현재 권한을 통과한 근거로 다시 구성됩니다.",
    open: (name) => `프로젝트 이력 열기: ${name}`,
    close: (name) => `프로젝트 이력 닫기: ${name}`,
    loading: "인용된 프로젝트 이력을 불러오는 중...",
    truncated: "일부 추가 프로젝트는 표시하지 않습니다. 인용된 원천 기록에서 프로젝트 근거를 확인하세요.",
    observed: "관찰된 프로젝트 식별자",
    inferred: "추론된 프로젝트 식별자",
  },
  zh: {
    heading: "此回答引用的项目历史",
    boundary: "每条时间线都根据回答截止时间和当前授权证据重新构建。",
    open: (name) => `打开项目历史：${name}`,
    close: (name) => `关闭项目历史：${name}`,
    loading: "正在加载引用的项目历史...",
    truncated: "还有引用项目未显示。请打开引用的源记录检查其项目依据。",
    observed: "已观察的项目身份",
    inferred: "已推断的项目身份",
  },
  ja: {
    heading: "この回答が引用したプロジェクト履歴",
    boundary: "各タイムラインは回答時点と現在の権限を通過した根拠から再構成されます。",
    open: (name) => `プロジェクト履歴を開く: ${name}`,
    close: (name) => `プロジェクト履歴を閉じる: ${name}`,
    loading: "引用されたプロジェクト履歴を読み込み中...",
    truncated: "追加の引用プロジェクトは表示されていません。引用元レコードでプロジェクト根拠を確認してください。",
    observed: "観察されたプロジェクト識別子",
    inferred: "推論されたプロジェクト識別子",
  },
  vi: {
    heading: "Lịch sử dự án được câu trả lời này trích dẫn",
    boundary: "Mỗi dòng thời gian được dựng lại từ bằng chứng hiện được cấp quyền tại thời điểm cắt của câu trả lời.",
    open: (name) => `Mở lịch sử dự án: ${name}`,
    close: (name) => `Đóng lịch sử dự án: ${name}`,
    loading: "Đang tải lịch sử dự án được trích dẫn...",
    truncated: "Một số dự án được trích dẫn chưa được hiển thị. Hãy mở bản ghi nguồn để kiểm tra bằng chứng dự án.",
    observed: "Danh tính dự án được quan sát",
    inferred: "Danh tính dự án được suy luận",
  },
};

function ProjectHistoryDisclosure({
  accessToken,
  link,
  onOpenPost,
}: {
  accessToken: string;
  link: ProjectHistoryLink;
  onOpenPost: (postId: string) => void;
}) {
  const locale = useLocale();
  const copy = COPY[locale];
  const regionId = useId();
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [projection, setProjection] = useState<ProjectHistoryProjection | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setOpened(false);
    setLoading(false);
    setProjection(null);
    setError(false);
  }, [link.project_key, link.focus_post_id, link.knowledge_cutoff]);

  function toggle() {
    if (opened) {
      setOpened(false);
      return;
    }
    setOpened(true);
    if (projection || loading) return;
    setLoading(true);
    setError(false);
    fetchProjectHistory(
      accessToken,
      link.project_key,
      link.knowledge_cutoff,
      link.focus_post_id,
    )
      .then((result) => {
        setProjection(result);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }

  return (
    <article className="ask-project-history-link">
      <div>
        <strong>{link.project_name}</strong>
        <span className="post-badge">
          {link.truth_status_code === "observed" ? copy.observed : copy.inferred}
        </span>
      </div>
      <button type="button" aria-expanded={opened} aria-controls={regionId} onClick={toggle}>
        {opened ? copy.close(link.project_name) : copy.open(link.project_name)}
      </button>
      <div id={regionId} hidden={!opened}>
        {loading ? <p role="status">{copy.loading}</p> : null}
        {error ? (
          <p role="alert">{projectHistoryText(locale, "historyUnavailable")}</p>
        ) : null}
        {!error && projection ? (
          <ProjectHistoryTimeline projection={projection} onOpenPost={onOpenPost} />
        ) : null}
      </div>
    </article>
  );
}

export function AskProjectHistoryLinks({
  accessToken,
  links,
  truncated,
  onOpenPost,
}: {
  accessToken: string;
  links: ProjectHistoryLink[];
  truncated: boolean;
  onOpenPost: (postId: string) => void;
}) {
  const locale = useLocale();
  const copy = COPY[locale];
  const headingId = useId();
  if (links.length === 0 && !truncated) return null;
  return (
    <section className="ask-project-history-links" aria-labelledby={headingId}>
      <h4 id={headingId}>{copy.heading}</h4>
      <p className="project-history-boundary">{copy.boundary}</p>
      {links.map((link) => (
        <ProjectHistoryDisclosure
          key={`${link.project_key}:${link.focus_post_id}:${link.knowledge_cutoff}`}
          accessToken={accessToken}
          link={link}
          onOpenPost={onOpenPost}
        />
      ))}
      {truncated ? <p role="status">{copy.truncated}</p> : null}
    </section>
  );
}
''',
    )
    write_new(
        "frontend/src/components/AskProjectHistoryLinks.css",
        r'''
.ask-project-history-links {
  display: grid;
  gap: 0.75rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color, #d7dce5);
}

.ask-project-history-links > h4,
.ask-project-history-link p {
  margin: 0;
}

.ask-project-history-link {
  display: grid;
  gap: 0.625rem;
  padding: 0.75rem;
  border: 1px solid var(--border-color, #d7dce5);
  border-radius: 0.75rem;
  background: var(--surface-color, #fff);
}

.ask-project-history-link > div:first-child {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.ask-project-history-link > button {
  justify-self: start;
}

.ask-project-history-link [hidden] {
  display: none;
}
''',
    )
    write_new(
        "frontend/src/components/AskProjectHistoryLinks.stories.tsx",
        r'''
import type { Meta, StoryObj } from "@storybook/react";

import { AskProjectHistoryLinks } from "./AskProjectHistoryLinks";

const meta = {
  title: "Buyer/Ask Project History Links",
  component: AskProjectHistoryLinks,
  args: {
    accessToken: "storybook-token",
    links: [
      {
        project_key: "P-100",
        project_name: "Synthetic renewal",
        focus_post_id: "post-voc",
        source_post_ids: ["post-spec", "post-voc"],
        knowledge_cutoff: "2026-08-20T12:00:00Z",
        truth_status_code: "observed",
      },
    ],
    truncated: false,
    onOpenPost: () => undefined,
  },
} satisfies Meta<typeof AskProjectHistoryLinks>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ObservedProject: Story = {};

export const InferredAndTruncated: Story = {
  args: {
    links: [
      {
        project_key: "semantic-project",
        project_name: "Semantic project candidate",
        focus_post_id: "post-candidate",
        source_post_ids: ["post-candidate"],
        knowledge_cutoff: "2026-08-20T12:00:00Z",
        truth_status_code: "inferred",
      },
    ],
    truncated: true,
  },
};
''',
    )


def patch_frontend_api_and_app() -> None:
    """Expose structured links and render them in both answer surfaces."""

    replace_once(
        "frontend/src/api.ts",
        """export interface CitedPostEvidence {
  post_id: string;
  facts: CitedPostEvidenceFact[];
}

export interface ChatAnswer {
""",
        """export interface CitedPostEvidence {
  post_id: string;
  facts: CitedPostEvidenceFact[];
}

export interface ProjectHistoryLink {
  project_key: string;
  project_name: string;
  focus_post_id: string;
  source_post_ids: string[];
  knowledge_cutoff: string;
  truth_status_code: "observed" | "inferred";
}

export interface ChatAnswer {
""",
    )
    replace_once(
        "frontend/src/api.ts",
        """  cited_posts?: CitedPostRef[];
  source_post_ids: string[];
}

export interface ChatExchange {
""",
        """  cited_posts?: CitedPostRef[];
  source_post_ids: string[];
  knowledge_cutoff?: string;
  project_histories?: ProjectHistoryLink[];
  project_histories_truncated?: boolean;
}

export interface ChatExchange {
""",
    )
    replace_once(
        "frontend/src/api.ts",
        """  cited_post_ids: string[];
  cited_posts?: CitedPostRef[];
}

export interface ChatHistory {
""",
        """  cited_post_ids: string[];
  cited_posts?: CitedPostRef[];
  knowledge_cutoff?: string;
  project_histories?: ProjectHistoryLink[];
  project_histories_truncated?: boolean;
}

export interface ChatHistory {
""",
    )
    replace_once(
        "frontend/src/api.ts",
        """  timeline?: AskTimelineEntry[];
  next_action?: string;
}
""",
        """  timeline?: AskTimelineEntry[];
  knowledge_cutoff?: string;
  project_histories?: ProjectHistoryLink[];
  project_histories_truncated?: boolean;
  next_action?: string;
}
""",
    )
    replace_once(
        "frontend/src/App.tsx",
        "  type PostSortOrder,\n",
        "  type PostSortOrder,\n  type ProjectHistoryLink,\n",
    )
    replace_once(
        "frontend/src/App.tsx",
        'import { ProjectHistoryTimeline } from "./components/ProjectHistoryTimeline";\n',
        'import { AskProjectHistoryLinks } from "./components/AskProjectHistoryLinks";\n'
        'import { ProjectHistoryTimeline } from "./components/ProjectHistoryTimeline";\n',
    )
    replace_once(
        "frontend/src/App.tsx",
        """          cited_post_ids: result.cited_post_ids,
          cited_posts: result.cited_posts,
        };
""",
        """          cited_post_ids: result.cited_post_ids,
          cited_posts: result.cited_posts,
          knowledge_cutoff: result.knowledge_cutoff,
          project_histories: result.project_histories,
          project_histories_truncated: result.project_histories_truncated,
        };
""",
    )
    first_citations = '''          <ChatCitations
            citedPosts={exchanges[0].cited_posts}
            citedPostIds={exchanges[0].cited_post_ids}
            onOpenEvidence={setEvidencePostId}
            currentPostId={
              exchanges[0].cited_posts?.[0]?.post_id ?? exchanges[0].cited_post_ids[0]
            }
          />
'''
    replace_once(
        "frontend/src/App.tsx",
        first_citations,
        first_citations
        + '''          <AskProjectHistoryLinks
            accessToken={accessToken}
            links={(exchanges[0].project_histories ?? []) as ProjectHistoryLink[]}
            truncated={exchanges[0].project_histories_truncated ?? false}
            onOpenPost={setEvidencePostId}
          />
''',
    )
    map_citations = '''          <ChatCitations
            citedPosts={exchange.cited_posts}
            citedPostIds={exchange.cited_post_ids}
            onOpenEvidence={setEvidencePostId}
          />
'''
    replace_once(
        "frontend/src/App.tsx",
        map_citations,
        map_citations
        + '''          <AskProjectHistoryLinks
            accessToken={accessToken}
            links={(exchange.project_histories ?? []) as ProjectHistoryLink[]}
            truncated={exchange.project_histories_truncated ?? false}
            onOpenPost={setEvidencePostId}
          />
''',
    )
    answer_citations = '''          <ChatCitations
            citedPosts={answer.cited_posts}
            citedPostIds={answer.cited_post_ids}
            onOpenEvidence={setEvidencePostId}
          />
'''
    replace_once(
        "frontend/src/App.tsx",
        answer_citations,
        answer_citations
        + '''          <AskProjectHistoryLinks
            accessToken={accessToken}
            links={(answer.project_histories ?? []) as ProjectHistoryLink[]}
            truncated={answer.project_histories_truncated ?? false}
            onOpenPost={setEvidencePostId}
          />
''',
    )
    replace_once(
        "frontend/src/App.tsx",
        """  async function handleAsk() {
    const normalized = question.trim();
    if (!normalized) return;
    setAsking(true);
    setError(null);
    setAnswer(null);
    try {
      const nextAnswer = await askAgent(accessToken, normalized, sessionId);
      setAnswer(nextAnswer);
      setSessionId(nextAnswer.session_id);
      window.sessionStorage.setItem("lineageweave.globalAskSessionId", nextAnswer.session_id);
    } catch (err) {
      setAnswer(null);
      setError(orchestratorUnavailableMessage(err, t("Ask Agent")));
    } finally {
      setAsking(false);
    }
  }
""",
        """  function acceptAnswer(nextAnswer: AskAgentResponse) {
    setAnswer(nextAnswer);
    setSessionId(nextAnswer.session_id);
    window.sessionStorage.setItem("lineageweave.globalAskSessionId", nextAnswer.session_id);
  }

  async function handleAsk() {
    const normalized = question.trim();
    if (!normalized) return;
    setAsking(true);
    setError(null);
    setAnswer(null);
    try {
      acceptAnswer(await askAgent(accessToken, normalized, sessionId));
    } catch (err) {
      if (err instanceof BackendError && err.status === 409 && sessionId) {
        window.sessionStorage.removeItem("lineageweave.globalAskSessionId");
        setSessionId(undefined);
        try {
          acceptAnswer(await askAgent(accessToken, normalized));
          return;
        } catch (retryError) {
          setError(orchestratorUnavailableMessage(retryError, t("Ask Agent")));
          return;
        }
      }
      setError(orchestratorUnavailableMessage(err, t("Ask Agent")));
    } finally {
      setAsking(false);
    }
  }
""",
    )
    timeline_block = '''          {answer.timeline && answer.timeline.length > 0 ? (
            <>
              <h4>Event Lineage timeline</h4>
              <ol className="related-post-list" aria-label="Event Lineage timeline">
                {answer.timeline.map((event) => (
                  <li key={event.post_id}>
                    <button
                      type="button"
                      className="post-list-item"
                      aria-label={`${t("Open timeline post:")} ${event.post_title}`}
                      onClick={() => onOpenPost(event.post_id)}
                    >
                      <strong>{event.post_title}</strong>
                      {event.occurred_at ? <time dateTime={event.occurred_at}>{event.occurred_at}</time> : null}
                    </button>
                  </li>
                ))}
              </ol>
            </>
          ) : null}
'''
    replace_once(
        "frontend/src/App.tsx",
        timeline_block,
        timeline_block
        + '''          <AskProjectHistoryLinks
            accessToken={accessToken}
            links={(answer.project_histories ?? []) as ProjectHistoryLink[]}
            truncated={answer.project_histories_truncated ?? false}
            onOpenPost={onOpenPost}
          />
''',
    )


def patch_docs_and_versions() -> None:
    """Record the closed Ask integration and advance the stacked release version."""

    replace_once("pyproject.toml", 'version = "2.19.0"\n', 'version = "2.20.0"\n')
    replace_once(
        "frontend/package.json",
        '  "version": "2.19.0",\n',
        '  "version": "2.20.0",\n',
    )
    replace_once(
        "uv.lock",
        'name = "lineageweave"\nversion = "2.19.0"\n',
        'name = "lineageweave"\nversion = "2.20.0"\n',
    )
    replace_once(
        "CHANGELOG.md",
        "## [2.19.0] - 2026-08-21\n",
        "## [2.20.0] - 2026-08-21\n\n"
        "### Added\n\n"
        "- Post-scoped Ask and Global Ask now attach exact project-history links derived\n"
        "  only from currently authorized cited posts. Opening a link reuses the canonical\n"
        "  Project history timeline and its optional TEPP validation at the answer cutoff.\n\n"
        "### Security\n\n"
        "- Persisted post answers are withheld when any citation is no longer visible, and\n"
        "  stale Global Ask sessions are restarted before hidden prior prose can re-enter\n"
        "  conversation context (ADR 0113).\n\n"
        "## [2.19.0] - 2026-08-21\n",
    )
    append_once(
        "docs/product-technical-gap-baseline.md",
        "## Ask-to-project-history integration (2026-08-21)",
        """
## Ask-to-project-history integration (2026-08-21)

- Post-scoped Ask and Global Ask return structured project-history links only for exact
  project identities on their currently authorized cited posts.
- Opening a link lazily calls the canonical Project history endpoint with the answer
  knowledge cutoff and cited focus post; no second timeline, classifier, or TEPP query is
  implemented in either Ask surface.
- Source publication eligibility and cutoff are applied before Ask retrieval. Persisted
  answers are withheld when any citation loses visibility, and a Global Ask session with
  stale citations must start a new session before prior answer prose is reused.
- The response bounds citation and project counts, discloses truncated project links, and
  keeps answers readable when a timeline or TEPP validation is unavailable.
- Remaining causal-analysis work is explicitly outside this slice: temporal association
  and evidence navigation do not identify why a VOC occurred.
""",
    )
    write_new(
        "docs/adr/0113-project-history-links-in-ask-surfaces.md",
        r'''
# ADR 0113: Reuse canonical project history in Ask surfaces

- Status: Proposed
- Date: 2026-08-21
- Depends on: ADR 0112 and the canonical Project history read model

## Context

Post-scoped Ask and Global Ask already cite authorized source posts, but they did not
connect those citations to the project lifecycle timeline shown in the product design.
The earlier orphaned stack attempted to solve this with another project-history flow.
That would create competing project identity, authorization, cutoff, classification, and
TEPP behavior.

Persisted Ask prose introduces an additional security boundary: if a previously cited
post becomes hidden, deleted, draft, or otherwise ineligible, returning the old answer or
reusing it as conversation context can disclose facts no longer authorized.

## Decision

1. Ask responses expose structured project-history links derived only from cited post IDs.
2. Citation IDs are reauthorized with tenant ABAC, source publication eligibility, and the
   answer knowledge cutoff before titles or project identities are returned.
3. Exact source project fields outrank semantic project candidates; inferred identities
   remain labelled inferred. Links are bounded and deterministic.
4. Opening a link calls the canonical Project history endpoint with project key, answer
   cutoff, and cited focus post. The established timeline and TEPP metadata are reused.
5. A persisted post answer is withheld in full when any citation is no longer authorized.
   Its prose cannot be safely decomposed by source after access changes.
6. A Global Ask session is rejected and restarted when any citation in its persisted
   continuity context is no longer authorized. Stored summaries are not reused across
   that boundary.
7. Ask retrieval itself applies the same cutoff and source eligibility before an LLM sees
   evidence. Prompt bodies, hidden IDs, and unauthorized project counts never enter the
   project-history link response.
8. Timeline or TEPP failure does not remove the answer; the Buyer receives an actionable
   error and can still open the exact cited source post.

## Consequences

- Document reading, post Ask, Global Ask, and the dedicated Project history destination
  share one authorization-first read model and one timeline component.
- Historical answers can disappear after permission or publication changes. This is an
  intentional fail-closed property, not data loss from the evidence store.
- A session restart can lose conversational convenience, but prevents a compressed
  summary from carrying hidden prose forward.
- Event order remains a temporal association and is not presented as causal inference.

## Rejected alternatives

- Parse project identities from answer prose. This is nondeterministic and ungrounded.
- Build a second project query or timeline inside Ask. This duplicates authority.
- Return a stored answer while merely hiding its citation chips. The prose may still leak
  the hidden source.
- Keep a stale Global Ask summary and filter only new citations. The summary cannot be
  safely decomposed after authorization changes.
''',
    )


def main() -> None:
    """Apply every product, test-support, and documentation edit."""

    create_backend_projection()
    patch_post_chat_ingestion()
    patch_main_routes()
    create_frontend_component()
    patch_frontend_api_and_app()
    patch_docs_and_versions()


if __name__ == "__main__":
    main()
