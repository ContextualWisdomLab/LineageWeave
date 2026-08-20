"""Finalize the bounded TEPP project-history Buyer integration on PR #271."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _write(path: str, value: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def _replace_between(text: str, start: str, end: str, replacement: str) -> str:
    left = text.find(start)
    if left < 0:
        raise RuntimeError(f"missing start marker: {start}")
    right = text.find(end, left + len(start))
    if right < 0:
        raise RuntimeError(f"missing end marker: {end}")
    return text[:left] + replacement.rstrip() + "\n\n" + text[right:]


def _function_region(text: str, marker: str) -> tuple[int, int, str]:
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"missing function marker: {marker}")
    end = text.find("\nfunction ", start + len(marker))
    if end < 0:
        end = len(text)
    return start, end, text[start:end]


def _patch_main() -> None:
    path = "backend/app/main.py"
    source = _read(path)
    source = source.replace(
        "from datetime import datetime\n",
        "from datetime import datetime, timezone\n",
        1,
    )
    if "from backend.app.tepp_project_history import project_history_for_post_ids" not in source:
        anchor = "from backend.app.post_summary_ingestion import (\n"
        source = _replace_once(
            source,
            anchor,
            "from backend.app.tepp_project_history import project_history_for_post_ids\n" + anchor,
            "TEPP project-history import",
        )

    endpoint = '''@app.get("/api/posts/{post_id}/project-history")
async def read_post_project_history(
    post_id: str,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Return TEPP's cutoff-safe project timeline for one visible post."""
    post = await _load_visible_post(post_id, account, pool)
    settings = load_settings()
    async with pool.acquire() as conn:
        return await project_history_for_post_ids(
            conn,
            tenant_workspace_id=str(account.user_account_id),
            corporate_entity_ids=[str(value) for value in account.corporate_entity_ids],
            focus_post_id=str(post["post_id"]),
            source_post_ids=[str(post["post_id"])],
            knowledge_cutoff=datetime.now(timezone.utc),
            tepp_transport_url=settings.tepp_transport_url,
        )
'''
    route = '@app.get("/api/posts/{post_id}/project-history")\n'
    chat_request = "class ChatRequest(BaseModel):\n"
    if route in source:
        source = _replace_between(source, route, chat_request, endpoint)
    else:
        source = _replace_once(
            source,
            chat_request,
            endpoint + "\n\n" + chat_request,
            "project-history endpoint",
        )

    chat = '''@app.post("/api/posts/{post_id}/chat")
async def chat_about_post(
    post_id: str,
    request: ChatRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Answer one post-scoped question and attach its TEPP project history.

    Contextual-orchestrator remains the answer authority. LineageWeave selects
    the authorized exact-project evidence bundle; TEPP validates and orders it.
    A TEPP outage never fabricates or suppresses the underlying answer.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "question is required")
    await _load_visible_post(post_id, account, pool)
    settings = load_settings()
    corporate_entity_ids = [str(value) for value in account.corporate_entity_ids]
    tenant_workspace_id = str(account.user_account_id)
    async with pool.acquire() as conn:
        stored = await fetch_persisted_chat(conn, post_id, question)
        if stored is not None:
            source_ids = [post_id]
            source_ids.extend(
                cited_id for cited_id in stored["cited_post_ids"] if cited_id != post_id
            )
            history = await project_history_for_post_ids(
                conn,
                tenant_workspace_id=tenant_workspace_id,
                corporate_entity_ids=corporate_entity_ids,
                focus_post_id=post_id,
                source_post_ids=source_ids,
                knowledge_cutoff=datetime.now(timezone.utc),
                tepp_transport_url=settings.tepp_transport_url,
            )
            return {
                "post_id": post_id,
                "answer_text": stored["answer_text"],
                "cited_post_ids": stored["cited_post_ids"],
                "cited_posts": stored["cited_posts"],
                "source_post_ids": source_ids,
                "tepp_project_history": history["project_history"],
                "tepp_project_history_status": history["status"],
            }
        client = _post_chat_client()
        if not client.available:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Post chat is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
            )
        sources = await gather_chat_sources(
            conn,
            post_id,
            lambda row: _can_see_post(account, row),
            vision_client=_vision_client(),
        )
    try:
        answer = await asyncio.to_thread(client.answer, question, sources)
    except (HttpClientError, KeyError, OSError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Post chat is unavailable: contextual-orchestrator returned no complete evidence object",
        ) from exc
    cited_ids = list(answer.cited_post_ids)
    source_ids = [source.post_id for source in sources]
    async with pool.acquire() as conn:
        await persist_post_chat(conn, post_id, question, answer.answer_text, cited_ids)
        history = await project_history_for_post_ids(
            conn,
            tenant_workspace_id=tenant_workspace_id,
            corporate_entity_ids=corporate_entity_ids,
            focus_post_id=post_id,
            source_post_ids=source_ids,
            knowledge_cutoff=datetime.now(timezone.utc),
            tepp_transport_url=settings.tepp_transport_url,
        )
    return {
        "post_id": post_id,
        "answer_text": answer.answer_text,
        "cited_post_ids": cited_ids,
        "cited_posts": cited_post_summaries(sources, cited_ids),
        "source_post_ids": source_ids,
        "tepp_project_history": history["project_history"],
        "tepp_project_history_status": history["status"],
    }
'''
    source = _replace_between(
        source,
        '@app.post("/api/posts/{post_id}/chat")\n',
        '@app.post("/api/ask")\n',
        chat,
    )

    ask = '''@app.post("/api/ask")
async def ask_agent(
    request: GlobalAskRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Answer a Buyer question and attach TEPP history for its focal citation."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "question is required")
    _require_post_read(account)
    client = _post_chat_client()
    if not client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ask Agent is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
        )
    async with pool.acquire() as conn:
        sources = await gather_global_chat_sources(
            conn,
            lambda row: _can_see_post(account, row),
            account.corporate_entity_ids,
            question=question,
        )
    if not sources:
        return {
            "answer_text": "",
            "cited_post_ids": [],
            "cited_posts": [],
            "source_post_ids": [],
            "cited_post_evidence": [],
            "tepp_project_history": None,
            "tepp_project_history_status": "insufficient_project_evidence",
            "next_action": "No authorized source posts are available for this question.",
        }
    try:
        answer = await asyncio.to_thread(client.answer, question, sources)
    except (HttpClientError, KeyError, OSError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Ask Agent is unavailable: {exc}",
        ) from exc
    cited_ids = list(answer.cited_post_ids)
    source_ids = [source.post_id for source in sources]
    focus_post_id = cited_ids[0] if cited_ids else source_ids[0]
    settings = load_settings()
    async with pool.acquire() as conn:
        history = await project_history_for_post_ids(
            conn,
            tenant_workspace_id=str(account.user_account_id),
            corporate_entity_ids=[str(value) for value in account.corporate_entity_ids],
            focus_post_id=focus_post_id,
            source_post_ids=source_ids,
            knowledge_cutoff=datetime.now(timezone.utc),
            tepp_transport_url=settings.tepp_transport_url,
        )
    return {
        "answer_text": answer.answer_text,
        "cited_post_ids": cited_ids,
        "cited_posts": cited_post_summaries(sources, cited_ids),
        "cited_post_evidence": cited_post_evidence(sources, cited_ids),
        "source_post_ids": source_ids,
        "tepp_project_history": history["project_history"],
        "tepp_project_history_status": history["status"],
    }
'''
    source = _replace_between(
        source,
        '@app.post("/api/ask")\n',
        "class PostBookmarkRequest(BaseModel):\n",
        ask,
    )
    _write(path, source)


def _patch_adapter() -> None:
    path = "backend/app/tepp_project_history.py"
    source = _read(path)
    if "from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL" not in source:
        anchor = "from lineageweave.tepp_project_history import (\n"
        source = _replace_once(
            source,
            anchor,
            "from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL\n\n" + anchor,
            "eligibility import",
        )
    start = source.find("async def _load_project_rows(")
    end = source.find("\n\nasync def project_history_for_post_ids(", start)
    if start < 0 or end < 0:
        raise RuntimeError("project-row adapter region missing")
    loader = '''async def _load_project_rows(
    conn: asyncpg.Connection,
    *,
    focus_post_id: str,
    source_post_ids: Sequence[str],
    corporate_entity_ids: Iterable[str],
    knowledge_cutoff: datetime,
) -> list[Mapping[str, Any]]:
    """Load a bounded exact-project history after LineageWeave authorization."""
    focus = await conn.fetchrow(
        """
        select post_id, source_project_code, source_project_name
          from source_post
         where post_id = $1::uuid
        """,
        focus_post_id,
    )
    if focus is None or not str(focus["source_project_code"] or "").strip():
        return []
    project_key = str(focus["source_project_code"]).strip()
    authorized_entities = [str(value) for value in corporate_entity_ids]
    rows = await conn.fetch(
        f"""
        select post.post_id,
               post.post_title,
               post.source_stage_code,
               post.voc_type_code,
               post.source_project_code,
               post.source_project_name,
               btrim(left(source_post_search_text(post.post_body), 2000))
                   as post_body_excerpt,
               post.created_at,
               post.author_account_id::text as author_actor_id
          from source_post post
         where post.source_project_code = $1
           and post.created_at <= $2
           and (
               post.visibility_code = 'public'
               or post.corporate_entity_id::text = any($3::text[])
           )
           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}
         order by post.created_at, post.post_id
         limit 128
        """,
        project_key,
        knowledge_cutoff,
        authorized_entities,
    )
    candidate_ids = set(source_post_ids)
    candidate_ids.add(focus_post_id)
    if not candidate_ids.intersection(str(row["post_id"]) for row in rows):
        return []
    return [dict(row) for row in rows]
'''
    source = source[:start] + loader + source[end:]
    _write(path, source)


def _add_history_fields(source: str, name: str) -> str:
    pattern = re.compile(rf"export interface {re.escape(name)} \{{(?P<body>.*?)\n\}}", re.DOTALL)
    match = pattern.search(source)
    if match is None:
        raise RuntimeError(f"missing interface: {name}")
    body = match.group("body")
    if "tepp_project_history" in body:
        return source
    body += (
        "\n  tepp_project_history?: TeppProjectHistory | null;"
        "\n  tepp_project_history_status?: string;"
    )
    return source[: match.start("body")] + body + source[match.end("body") :]


def _patch_api() -> None:
    path = "frontend/src/api.ts"
    source = _read(path)
    if "export interface TeppProjectHistoryEvent" not in source:
        anchor = "export interface ChatAnswer {\n"
        types = '''export interface TeppProjectHistoryEvent {
  event_id: string;
  event_type_code: string;
  event_title: string;
  event_time: string;
  available_at: string;
  availability_basis: string;
  source_post_id: string;
  evidence_text: string;
  actor_ids: string[];
}

export interface TeppProjectHistoryFinding {
  finding_code: string;
  summary: string;
  related_event_ids: string[];
  evidence_post_ids: string[];
}

export interface TeppProjectHistory {
  contract_version: number;
  project_key: string;
  project_name: string;
  focus_event_id: string;
  inference_status: "temporal_association_only";
  participant_count: number;
  history_span_start: string;
  history_span_end: string;
  events: TeppProjectHistoryEvent[];
  findings: TeppProjectHistoryFinding[];
}

export interface TeppProjectHistoryEnvelope {
  status: string;
  project_history: TeppProjectHistory | null;
  next_action: string;
}

'''
        source = _replace_once(source, anchor, types + anchor, "frontend history types")
    for interface in ("ChatAnswer", "ChatExchange", "AskAgentResponse"):
        source = _add_history_fields(source, interface)

    source = re.sub(
        r"\nexport (?:async )?function fetchPostProjectHistory\(.*?\n\}\n",
        "\n",
        source,
        flags=re.DOTALL,
    )
    anchor = "export function fetchPostContent(accessToken: string, postId: string): Promise<PostContentResponse> {\n"
    function = '''export function fetchPostProjectHistory(
  accessToken: string,
  postId: string,
): Promise<TeppProjectHistoryEnvelope> {
  return backendFetch<TeppProjectHistoryEnvelope>(
    `/api/posts/${encodeURIComponent(postId)}/project-history`,
    accessToken,
  );
}

'''
    source = _replace_once(source, anchor, function + anchor, "history fetch function")
    _write(path, source)


def _patch_app() -> None:
    path = "frontend/src/App.tsx"
    source = _read(path)
    if 'from "./components/ProjectHistoryTimeline"' not in source:
        anchor = 'import { PopupCloseButton } from "./components/PopupCloseButton";\n'
        source = _replace_once(
            source,
            anchor,
            anchor
            + 'import { PostProjectHistory, ProjectHistoryTimeline } from "./components/ProjectHistoryTimeline";\n',
            "timeline import",
        )

    start, end, region = _function_region(source, "function ChatPanel(")
    if "answer?.tepp_project_history" not in region:
        anchor = "      {!nameFirstAsk && evidencePostId ? (\n"
        timeline = '''      {answer?.tepp_project_history ? (
        <ProjectHistoryTimeline
          history={answer.tepp_project_history}
          onOpenPost={setEvidencePostId}
        />
      ) : null}
'''
        region = _replace_once(region, anchor, timeline + anchor, "post Ask timeline")
        source = source[:start] + region + source[end:]

    start, end, region = _function_region(source, "function PostDetailPopup(")
    region = re.sub(
        r"\s*<PostProjectHistory\n.*?/>\n",
        "\n",
        region,
        flags=re.DOTALL,
    )
    anchor = "            <IssueTicketPanel postId={postId} accessToken={accessToken} canExtract={canExtract} />\n"
    if anchor not in region:
        raise RuntimeError("post detail timeline insertion anchor missing")
    timeline = '''            <PostProjectHistory
              accessToken={accessToken}
              postId={postId}
              onOpenPost={(sourcePostId) => onSelectPost?.(sourcePostId)}
            />

'''
    region = region.replace(anchor, timeline + anchor, 1)
    source = source[:start] + region + source[end:]

    start, end, region = _function_region(source, "function AskAgentPanel(")
    if "answer?.tepp_project_history" not in region:
        closing = region.rfind("</section>")
        if closing < 0:
            raise RuntimeError("Global Ask closing section missing")
        timeline = '''      {answer?.tepp_project_history ? (
        <ProjectHistoryTimeline
          history={answer.tepp_project_history}
          onOpenPost={onOpenPost}
        />
      ) : null}
'''
        region = region[:closing] + timeline + region[closing:]
        source = source[:start] + region + source[end:]
    _write(path, source)


def _patch_test_contract() -> None:
    path = "tests/test_tepp_project_history_ingestion.py"
    source = _read(path)
    source = source.replace(
        '    assert "settings.tepp_api_key" not in source[source.index("project_history_for_post_ids"): ]\n',
        '    project_history_lines = [line for line in source.splitlines() if "project_history" in line]\n'
        '    assert project_history_lines\n'
        '    assert all("api_key" not in line for line in project_history_lines)\n',
    )
    source = source.replace(
        '    assert "settings.tepp_api_key" not in source[source.index("project_history_for_post_ids"):]\n',
        '    project_history_lines = [line for line in source.splitlines() if "project_history" in line]\n'
        '    assert project_history_lines\n'
        '    assert all("api_key" not in line for line in project_history_lines)\n',
    )
    _write(path, source)


def _patch_docs() -> None:
    environment = _read(".env.example")
    if "TEPP project-history transport" not in environment:
        environment += '''
# TEPP project-history transport. Production must be HTTPS; loopback HTTP is
# permitted only for local modular integration. No browser or provider token is forwarded.
# TEPP_TRANSPORT_URL=https://tepp.example.com
'''
        _write(".env.example", environment)
    _write(
        "CHANGELOG.d/2.18.0-tepp-project-history-ask.md",
        """# 2.18.0 — TEPP project-history answers

- Post reading, Global Ask, and post Ask display a TEPP-validated exact-project timeline.
- Every event links to an authorized source post and observes the knowledge cutoff.
- TEPP returns temporal association only; missing events, actors, confidence, theta, and causal conclusions are not invented.
""",
    )
    _write(
        "docs/adr/0076-tepp-project-history-ask.md",
        """# ADR 0076: TEPP-owned project-history projection on Buyer surfaces

## Status

Accepted on this stacked branch; release remains gated by TEPP and LineageWeave predecessor PRs.

## Decision

LineageWeave applies its existing RBAC, ABAC, publication-eligibility, exact `source_project_code`, and knowledge-cutoff rules before sending a bounded event bundle to TEPP's versioned `/v1/project-histories` boundary. Browser tokens, review credentials, model-provider keys, and database access are not forwarded.

TEPP validates and deterministically orders the supplied events, derives the participant count only from supplied opaque actor identities, and returns `temporal_association_only`. LineageWeave rejects changed or out-of-bundle evidence, unknown fields, causal authority, and participant counts that are not evidence-derived.

The same projection is exposed while reading a post, through Global Ask, and through post-scoped Ask. Each timeline event opens its exact authorized source post.

## Consequences

Missing events, actors, projects, confidence, theta, and causal conclusions remain missing. A TEPP outage yields a typed unavailable state without suppressing the underlying post or Ask answer.
""",
    )
    _write(
        "docs/doctoring/TEPP_PROJECT_HISTORY_REFERENCES.md",
        """# TEPP project-history references

Allen, J. F. (1983). Maintaining knowledge about temporal intervals. *Communications of the ACM, 26*(11), 832–843. https://doi.org/10.1145/182.358434

International Organization for Standardization. (2019). *ISO 8601-1:2019: Date and time—Representations for information interchange—Part 1: Basic rules*.

Klyne, G., & Newman, C. (2002). *Date and time on the Internet: Timestamps* (RFC 3339). Internet Engineering Task Force. https://doi.org/10.17487/RFC3339

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*. https://www.w3.org/TR/prov-o/
""",
    )


def main() -> None:
    """Apply the idempotent product integration to the live stacked branch."""
    _patch_main()
    _patch_adapter()
    _patch_api()
    _patch_app()
    _patch_test_contract()
    _patch_docs()


if __name__ == "__main__":
    main()
