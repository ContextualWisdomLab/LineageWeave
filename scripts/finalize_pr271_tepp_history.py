"""Finalize the bounded TEPP project-history Buyer integration on PR #271."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def replace_route(text: str, function_name: str, replacement: str) -> str:
    pattern = re.compile(
        rf'@app\.(?:get|post|patch|delete)\([^\n]+\)\nasync def {re.escape(function_name)}\(.*?(?=\n\n@app\.|\Z)',
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise RuntimeError(f"route not found: {function_name}")
    return text[: match.start()] + replacement.rstrip() + text[match.end() :]


def replace_async_function(text: str, function_name: str, replacement: str) -> str:
    pattern = re.compile(
        rf'async def {re.escape(function_name)}\(.*?(?=\n\n(?:async )?def |\n\nclass |\Z)',
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise RuntimeError(f"async function not found: {function_name}")
    return text[: match.start()] + replacement.rstrip() + text[match.end() :]


def patch_client() -> None:
    path = "lineageweave/tepp_project_history.py"
    text = read(path)
    if "from ipaddress import ip_address" not in text:
        text = replace_once(
            text,
            "from datetime import datetime, timezone\n",
            "from datetime import datetime, timezone\nfrom ipaddress import ip_address\n",
            "loopback import",
        )
    helper = '''\n\ndef _is_loopback_hostname(hostname: str) -> bool:\n    """Return whether a parsed TEPP hostname is local loopback."""\n    if hostname.casefold() == "localhost":\n        return True\n    try:\n        return ip_address(hostname).is_loopback\n    except ValueError:\n        return False\n'''
    if "def _is_loopback_hostname(" not in text:
        text = text.replace("\ndef project_history_endpoint(", helper + "\n\ndef project_history_endpoint(", 1)
    endpoint = '''def project_history_endpoint(transport_url: str) -> str:\n    """Resolve the TEPP path from clean HTTPS or local loopback HTTP."""\n    candidate = transport_url.strip()\n    if not candidate:\n        raise TeppProjectHistoryUnavailable("TEPP project-history transport is not configured")\n    parsed = urlsplit(candidate)\n    if (\n        not parsed.hostname\n        or parsed.username is not None\n        or parsed.password is not None\n        or parsed.query\n        or parsed.fragment\n        or parsed.scheme not in {"https", "http"}\n        or (parsed.scheme == "http" and not _is_loopback_hostname(parsed.hostname))\n    ):\n        raise TeppProjectHistoryUnavailable(\n            "TEPP project-history URL must use HTTPS or loopback HTTP"\n        )\n    path = parsed.path.rstrip("/")\n    if path.endswith("/v1/analysis-runs"):\n        path = path[: -len("/v1/analysis-runs")]\n    elif path and path != "/":\n        raise TeppProjectHistoryUnavailable("TEPP transport URL has an unsupported path")\n    return urlunsplit((parsed.scheme, parsed.netloc, f"{path}{PROJECT_HISTORY_PATH}", "", ""))\n'''
    pattern = re.compile(
        r"def project_history_endpoint\(transport_url: str\) -> str:.*?(?=\n\nTransport =)",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise RuntimeError("project_history_endpoint not found")
    text = text[: match.start()] + endpoint.rstrip() + text[match.end() :]
    write(path, text)


def patch_adapter() -> None:
    path = "backend/app/tepp_project_history.py"
    text = read(path)
    if "from .post_eligibility import SOURCE_POST_ELIGIBILITY_SQL" not in text:
        marker = "from lineageweave.tepp_project_history import ("
        block_end = text.index("\n)\n", text.index(marker)) + 3
        text = text[:block_end] + "\nfrom .post_eligibility import SOURCE_POST_ELIGIBILITY_SQL\n" + text[block_end:]
    loader = '''async def _load_project_rows(\n    conn: asyncpg.Connection,\n    *,\n    focus_post_id: str,\n    source_post_ids: Sequence[str],\n    corporate_entity_ids: Iterable[str],\n    knowledge_cutoff: datetime,\n) -> list[Mapping[str, Any]]:\n    """Load every eligible authorized post in the focus post's exact project."""\n    del source_post_ids\n    entity_ids = [str(value) for value in corporate_entity_ids]\n    focus = await conn.fetchrow(\n        f"""\n        select post.post_id, post.source_project_code, post.source_project_name\n          from source_post post\n         where post.post_id = $1::uuid\n           and post.created_at <= $2\n           and (\n               post.visibility_code = 'public'\n               or post.corporate_entity_id::text = any($3::text[])\n           )\n           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}\n        """,\n        focus_post_id,\n        knowledge_cutoff,\n        entity_ids,\n    )\n    if focus is None or not str(focus["source_project_code"] or "").strip():\n        return []\n    project_key = str(focus["source_project_code"]).strip()\n    rows = await conn.fetch(\n        f"""\n        select post.post_id,\n               post.post_title,\n               post.source_stage_code,\n               post.voc_type_code,\n               post.source_project_code,\n               post.source_project_name,\n               btrim(left(source_post_search_text(post.post_body), 2000)) as post_body_excerpt,\n               post.created_at,\n               post.author_account_id::text as author_actor_id,\n               coalesce(actors.actor_ids, array['account:' || post.author_account_id::text])\n                   as actor_ids\n          from source_post post\n          left join lateral (\n              select array_agg(distinct actor.actor_id order by actor.actor_id) as actor_ids\n                from (\n                    select 'account:' || post.author_account_id::text as actor_id\n                    union all\n                    select case\n                             when role.cataloged_person_id is not null\n                               then 'person:' || role.cataloged_person_id::text\n                             when role.cataloged_team_id is not null\n                               then 'team:' || role.cataloged_team_id::text\n                             when role.cataloged_corporate_entity_id is not null\n                               then 'organization:' || role.cataloged_corporate_entity_id::text\n                             else null\n                           end as actor_id\n                      from post_summary_role role\n                     where role.post_id = post.post_id\n                ) actor\n               where actor.actor_id is not null\n          ) actors on true\n         where post.source_project_code = $1\n           and post.created_at <= $2\n           and (\n               post.visibility_code = 'public'\n               or post.corporate_entity_id::text = any($3::text[])\n           )\n           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}\n         order by post.created_at, post.post_id\n         limit 128\n        """,\n        project_key,\n        knowledge_cutoff,\n        entity_ids,\n    )\n    return [dict(row) for row in rows]\n'''
    text = replace_async_function(text, "_load_project_rows", loader)
    text = text.replace(
        "tenant_workspace_id=tenant_workspace_id,",
        "tenant_workspace_id=str(tenant_workspace_id),",
    )
    write(path, text)


def patch_main() -> None:
    path = "backend/app/main.py"
    text = read(path)
    if "from datetime import datetime, timezone" not in text:
        text = text.replace("from datetime import datetime\n", "from datetime import datetime, timezone\n", 1)
    if "from backend.app.tepp_project_history import project_history_for_post_ids" not in text:
        text = replace_once(
            text,
            "from backend.app.post_summary_ingestion import (",
            "from backend.app.tepp_project_history import project_history_for_post_ids\n"
            "from backend.app.post_summary_ingestion import (",
            "TEPP adapter import",
        )
    endpoint = '''@app.get("/api/posts/{post_id}/project-history")\nasync def read_post_project_history(\n    post_id: str,\n    as_of: str | None = None,\n    account: CurrentAccount = Depends(get_current_account),\n    pool: asyncpg.Pool = Depends(get_pool),\n) -> dict[str, Any]:\n    """Return TEPP's cutoff-safe history for one authorized project post."""\n    await _load_visible_post(post_id, account, pool)\n    if as_of is None:\n        cutoff = datetime.now(timezone.utc)\n    else:\n        try:\n            cutoff = parse_as_of_clock(as_of)\n        except ValueError as exc:\n            raise HTTPException(\n                status.HTTP_422_UNPROCESSABLE_ENTITY,\n                "as_of must be an ISO-8601 timestamp for the project-history cutoff.",\n            ) from exc\n    async with pool.acquire() as conn:\n        return await project_history_for_post_ids(\n            conn,\n            tenant_workspace_id=str(account.user_account_id),\n            corporate_entity_ids=account.corporate_entity_ids,\n            focus_post_id=post_id,\n            source_post_ids=[post_id],\n            knowledge_cutoff=cutoff,\n            tepp_transport_url=load_settings().tepp_transport_url,\n        )\n'''
    existing = re.search(
        r'@app\.get\("/api/posts/\{post_id\}/project-history"\).*?(?=\n\n@app\.|\Z)',
        text,
        re.DOTALL,
    )
    if existing is None:
        text = replace_once(
            text,
            '@app.get("/api/posts/{post_id}/chat")',
            endpoint + '\n\n\n@app.get("/api/posts/{post_id}/chat")',
            "project-history route",
        )
    else:
        text = text[: existing.start()] + endpoint.rstrip() + text[existing.end() :]
    chat = '''@app.post("/api/posts/{post_id}/chat")\nasync def chat_about_post(\n    post_id: str,\n    request: ChatRequest,\n    account: CurrentAccount = Depends(get_current_account),\n    pool: asyncpg.Pool = Depends(get_pool),\n) -> dict[str, Any]:\n    """Answer from authorized lineage evidence and attach TEPP project history."""\n    question = request.question.strip()\n    if not question:\n        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "question is required")\n    await _load_visible_post(post_id, account, pool)\n    settings = load_settings()\n    async with pool.acquire() as conn:\n        stored = await fetch_persisted_chat(conn, post_id, question)\n        if stored is not None:\n            source_ids = [post_id]\n            source_ids.extend(cid for cid in stored["cited_post_ids"] if cid != post_id)\n            history = await project_history_for_post_ids(\n                conn,\n                tenant_workspace_id=str(account.user_account_id),\n                corporate_entity_ids=account.corporate_entity_ids,\n                focus_post_id=post_id,\n                source_post_ids=source_ids,\n                knowledge_cutoff=datetime.now(timezone.utc),\n                tepp_transport_url=settings.tepp_transport_url,\n            )\n            return {\n                "post_id": post_id,\n                "answer_text": stored["answer_text"],\n                "cited_post_ids": stored["cited_post_ids"],\n                "cited_posts": stored["cited_posts"],\n                "source_post_ids": source_ids,\n                "tepp_project_history": history["project_history"],\n                "tepp_project_history_status": history["status"],\n            }\n        client = _post_chat_client()\n        if not client.available:\n            raise HTTPException(\n                status.HTTP_503_SERVICE_UNAVAILABLE,\n                "Post chat is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",\n            )\n        sources = await gather_chat_sources(\n            conn, post_id, lambda row: _can_see_post(account, row), vision_client=_vision_client()\n        )\n    try:\n        answer = await asyncio.to_thread(client.answer, question, sources)\n    except (HttpClientError, KeyError, OSError, ValueError) as exc:\n        raise HTTPException(\n            status.HTTP_503_SERVICE_UNAVAILABLE,\n            "Post chat is unavailable: contextual-orchestrator returned no complete evidence object",\n        ) from exc\n    cited_ids = list(answer.cited_post_ids)\n    async with pool.acquire() as conn:\n        await persist_post_chat(conn, post_id, question, answer.answer_text, cited_ids)\n        history = await project_history_for_post_ids(\n            conn,\n            tenant_workspace_id=str(account.user_account_id),\n            corporate_entity_ids=account.corporate_entity_ids,\n            focus_post_id=post_id,\n            source_post_ids=[source.post_id for source in sources],\n            knowledge_cutoff=datetime.now(timezone.utc),\n            tepp_transport_url=settings.tepp_transport_url,\n        )\n    return {\n        "post_id": post_id,\n        "answer_text": answer.answer_text,\n        "cited_post_ids": cited_ids,\n        "cited_posts": cited_post_summaries(sources, cited_ids),\n        "source_post_ids": [source.post_id for source in sources],\n        "tepp_project_history": history["project_history"],\n        "tepp_project_history_status": history["status"],\n    }\n'''
    text = replace_route(text, "chat_about_post", chat)
    ask = '''@app.post("/api/ask")\nasync def ask_agent(\n    request: GlobalAskRequest,\n    account: CurrentAccount = Depends(get_current_account),\n    pool: asyncpg.Pool = Depends(get_pool),\n) -> dict[str, Any]:\n    """Answer a Buyer question and attach the cited project's TEPP history."""\n    question = request.question.strip()\n    if not question:\n        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "question is required")\n    _require_post_read(account)\n    client = _post_chat_client()\n    if not client.available:\n        raise HTTPException(\n            status.HTTP_503_SERVICE_UNAVAILABLE,\n            "Ask Agent is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",\n        )\n    async with pool.acquire() as conn:\n        sources = await gather_global_chat_sources(\n            conn,\n            lambda row: _can_see_post(account, row),\n            account.corporate_entity_ids,\n            question=question,\n        )\n    if not sources:\n        return {\n            "answer_text": "",\n            "cited_post_ids": [],\n            "cited_posts": [],\n            "source_post_ids": [],\n            "cited_post_evidence": [],\n            "tepp_project_history": None,\n            "tepp_project_history_status": "insufficient_project_evidence",\n            "next_action": "No authorized source posts are available for this question.",\n        }\n    try:\n        answer = await asyncio.to_thread(client.answer, question, sources)\n    except (HttpClientError, KeyError, OSError, ValueError) as exc:\n        raise HTTPException(\n            status.HTTP_503_SERVICE_UNAVAILABLE, f"Ask Agent is unavailable: {exc}"\n        ) from exc\n    cited_ids = list(answer.cited_post_ids)\n    focus_post_id = cited_ids[0] if cited_ids else sources[0].post_id\n    async with pool.acquire() as conn:\n        history = await project_history_for_post_ids(\n            conn,\n            tenant_workspace_id=str(account.user_account_id),\n            corporate_entity_ids=account.corporate_entity_ids,\n            focus_post_id=focus_post_id,\n            source_post_ids=[source.post_id for source in sources],\n            knowledge_cutoff=datetime.now(timezone.utc),\n            tepp_transport_url=load_settings().tepp_transport_url,\n        )\n    return {\n        "answer_text": answer.answer_text,\n        "cited_post_ids": cited_ids,\n        "cited_posts": cited_post_summaries(sources, cited_ids),\n        "cited_post_evidence": cited_post_evidence(sources, cited_ids),\n        "source_post_ids": [source.post_id for source in sources],\n        "tepp_project_history": history["project_history"],\n        "tepp_project_history_status": history["status"],\n    }\n'''
    text = replace_route(text, "ask_agent", ask)
    write(path, text)


def add_interface_fields(text: str, interface: str) -> str:
    pattern = re.compile(rf"export interface {interface} \{{(?P<body>.*?)\n\}}", re.DOTALL)
    match = pattern.search(text)
    if match is None:
        raise RuntimeError(f"interface not found: {interface}")
    body = match.group("body")
    if "tepp_project_history" in body:
        return text
    body += "\n  tepp_project_history?: TeppProjectHistory | null;"
    body += "\n  tepp_project_history_status?: string;"
    return text[: match.start("body")] + body + text[match.end("body") :]


def patch_api() -> None:
    path = "frontend/src/api.ts"
    text = read(path)
    if "export interface TeppProjectHistoryEvent" not in text:
        types = '''export interface TeppProjectHistoryEvent {\n  event_id: string;\n  event_type_code: string;\n  event_title: string;\n  event_time: string;\n  available_at: string;\n  availability_basis: string;\n  source_post_id: string;\n  evidence_text: string;\n  actor_ids: string[];\n}\n\nexport interface TeppProjectHistoryFinding {\n  finding_code: string;\n  summary: string;\n  related_event_ids: string[];\n  evidence_post_ids: string[];\n}\n\nexport interface TeppProjectHistory {\n  contract_version: number;\n  project_key: string;\n  project_name: string;\n  focus_event_id: string;\n  inference_status: "temporal_association_only";\n  participant_count: number;\n  history_span_start: string;\n  history_span_end: string;\n  events: TeppProjectHistoryEvent[];\n  findings: TeppProjectHistoryFinding[];\n}\n\nexport interface TeppProjectHistoryEnvelope {\n  status: string;\n  project_history: TeppProjectHistory | null;\n  next_action: string;\n}\n\n'''
        text = replace_once(text, "export interface ChatAnswer {", types + "export interface ChatAnswer {", "API types")
    text = add_interface_fields(text, "ChatAnswer")
    text = add_interface_fields(text, "AskAgentResponse")
    if "export function fetchPostProjectHistory(" not in text:
        client = '''export function fetchPostProjectHistory(\n  accessToken: string,\n  postId: string,\n  asOf?: string,\n): Promise<TeppProjectHistoryEnvelope> {\n  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";\n  return backendFetch<TeppProjectHistoryEnvelope>(\n    `/api/posts/${postId}/project-history${query}`,\n    accessToken,\n  );\n}\n\n'''
        text = replace_once(text, "export function fetchPostContent(", client + "export function fetchPostContent(", "API client")
    write(path, text)


def patch_component() -> None:
    path = "frontend/src/components/ProjectHistoryTimeline.tsx"
    text = read(path)
    if "knowledgeCutoff?: string | null;" not in text:
        text = replace_once(
            text,
            "  onOpenPost: (postId: string) => void;\n}) {",
            "  onOpenPost: (postId: string) => void;\n  knowledgeCutoff?: string | null;\n}) {",
            "component cutoff prop",
        )
        text = text.replace("  onOpenPost,\n}: {", "  onOpenPost,\n  knowledgeCutoff,\n}: {", 1)
    text = text.replace(
        "fetchPostProjectHistory(accessToken, postId)",
        "fetchPostProjectHistory(accessToken, postId, knowledgeCutoff ?? undefined)",
    )
    text = text.replace(
        "}, [accessToken, postId]);",
        "}, [accessToken, knowledgeCutoff, postId]);",
        1,
    )
    write(path, text)


def patch_app() -> None:
    path = "frontend/src/App.tsx"
    text = read(path)
    prefix = text.split("function LanguageSwitcher", 1)[0]
    if 'from "./components/ProjectHistoryTimeline"' not in prefix:
        text = replace_once(
            text,
            'import { BuyerNav, type BuyerDestination } from "./components/BuyerNav";\n',
            'import { BuyerNav, type BuyerDestination } from "./components/BuyerNav";\n'
            'import { PostProjectHistory, ProjectHistoryTimeline } from "./components/ProjectHistoryTimeline";\n',
            "App component import",
        )
    if "type TeppProjectHistory," not in text:
        text = replace_once(
            text,
            "  type VocEvidence,\n",
            "  type VocEvidence,\n  type TeppProjectHistory,\n",
            "App API type",
        )
    start = text.index("function ChatPanel(")
    end = text.index("\nfunction eventLineageCurrentNextAction", start)
    chat = text[start:end]
    if "teppHistory" not in chat:
        chat = replace_once(
            chat,
            "  const [answer, setAnswer] = useState<ChatAnswer | null>(null);\n",
            "  const [answer, setAnswer] = useState<ChatAnswer | null>(null);\n"
            "  const [teppHistory, setTeppHistory] = useState<TeppProjectHistory | null>(null);\n",
            "Chat TEPP state",
        )
        chat = replace_once(chat, "    setAnswer(null);\n", "    setAnswer(null);\n    setTeppHistory(null);\n", "Chat reset")
        chat = replace_once(
            chat,
            "      setAnswer(result);\n",
            "      setAnswer(result);\n      setTeppHistory(result.tepp_project_history ?? null);\n",
            "Chat result",
        )
        chat = replace_once(
            chat,
            "      {!nameFirstAsk && evidencePostId ? (\n",
            "      {teppHistory ? (\n"
            "        <ProjectHistoryTimeline history={teppHistory} onOpenPost={setEvidencePostId} />\n"
            "      ) : null}\n"
            "      {!nameFirstAsk && evidencePostId ? (\n",
            "Chat timeline",
        )
        text = text[:start] + chat + text[end:]
    ask_start = text.index("function AskAgentPanel(")
    ask_end = text.find("\nfunction ", ask_start + 10)
    if ask_end < 0:
        ask_end = len(text)
    ask = text[ask_start:ask_end]
    if "answer.tepp_project_history" not in ask:
        anchor = "          {answer.cited_posts"
        if anchor not in ask:
            anchor = "          {answer.cited_post_ids"
        if anchor not in ask:
            raise RuntimeError("Ask Agent citation anchor not found")
        ask = ask.replace(
            anchor,
            "          {answer.tepp_project_history ? (\n"
            "            <ProjectHistoryTimeline history={answer.tepp_project_history} onOpenPost={onOpenPost} />\n"
            "          ) : null}\n" + anchor,
            1,
        )
        text = text[:ask_start] + ask + text[ask_end:]
    popup_start = text.index("function PostDetailPopup(")
    popup_end = text.find("\nfunction ", popup_start + 10)
    if popup_end < 0:
        popup_end = len(text)
    popup = text[popup_start:popup_end]
    if "<PostProjectHistory" not in popup:
        anchor = "            <IssueTicketPanel postId={postId} accessToken={accessToken} canExtract={canExtract} />\n"
        if anchor not in popup:
            raise RuntimeError("Post popup history anchor not found")
        history = "            <PostProjectHistory\n"
        history += "              accessToken={accessToken}\n"
        history += "              postId={postId}\n"
        history += "              knowledgeCutoff={knowledgeCutoff}\n"
        history += "              onOpenPost={(eventPostId) => onSelectPost?.(eventPostId)}\n"
        history += "            />\n\n"
        popup = popup.replace(anchor, history + anchor, 1)
        text = text[:popup_start] + popup + text[popup_end:]
    write(path, text)


def patch_tests_and_docs() -> None:
    test_path = "tests/test_tepp_project_history.py"
    test = read(test_path)
    loopback = '    assert project_history_endpoint("http://127.0.0.1:9000") == "http://127.0.0.1:9000/v1/project-histories"\n'
    if loopback not in test:
        anchor = '    for hostile in ("", "file:///tmp/tepp", "http://tepp.example.test", "https://user@host"):\n'
        test = replace_once(test, anchor, loopback + anchor, "loopback regression")
    write(test_path, test)
    contract_path = "tests/test_tepp_project_history_ingestion.py"
    contract = read(contract_path)
    contract = contract.replace(
        '    assert source.count("project_history_for_post_ids(") >= 3\n',
        '    assert source.count("project_history_for_post_ids(") >= 4\n',
    )
    contract = contract.replace(
        '    assert "settings.tepp_api_key" not in source[source.index("project_history_for_post_ids"): ]\n',
        '    history_lines = [line for line in source.splitlines() if "project_history" in line]\n'
        '    assert history_lines\n'
        '    assert all("api_key" not in line for line in history_lines)\n',
    )
    contract = contract.replace(
        '    assert "settings.tepp_api_key" not in source[source.index("project_history_for_post_ids"):]\n',
        '    history_lines = [line for line in source.splitlines() if "project_history" in line]\n'
        '    assert history_lines\n'
        '    assert all("api_key" not in line for line in history_lines)\n',
    )
    write(contract_path, contract)
    write(
        "CHANGELOG.d/2.18.0-tepp-project-history-ask.md",
        "# 2.18.0 — TEPP project-history answers\n\n"
        "- Post reading, Global Ask, and post Ask display a TEPP-validated exact-project timeline.\n"
        "- Events link to authorized source posts and respect the knowledge cutoff.\n"
        "- TEPP returns temporal association only; missing events, actors, theta, confidence, and causal conclusions are not invented.\n",
    )
    env_path = ".env.example"
    env = read(env_path)
    if "TEPP project-history" not in env:
        env += "\n# TEPP project-history uses TEPP_TRANSPORT_URL without forwarding user or provider credentials.\n"
        env += "# Loopback HTTP is local-only; non-loopback deployments require HTTPS.\n"
        write(env_path, env)


def main() -> None:
    patch_client()
    patch_adapter()
    patch_main()
    patch_api()
    patch_component()
    patch_app()
    patch_tests_and_docs()


if __name__ == "__main__":
    main()
