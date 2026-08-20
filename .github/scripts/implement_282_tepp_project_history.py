"""Implement the clean TEPP project-history Buyer vertical on PR #282.

The script is deliberately exact-anchor based.  It runs only on a branch whose
parent is the current #264 head, applies the production change, writes the
release/ADR evidence, and leaves a path manifest for the one-shot workflow.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    """Read one repository UTF-8 file."""
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    """Write one repository UTF-8 file, creating parent directories."""
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    """Replace exactly one source anchor and fail closed on branch drift."""
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def function_region(source: str, marker: str, *, next_markers: tuple[str, ...]) -> tuple[int, int, str]:
    """Return one Python/TypeScript function region bounded by later markers."""
    start = source.find(marker)
    if start < 0:
        raise RuntimeError(f"function marker not found: {marker}")
    candidates = [source.find(candidate, start + len(marker)) for candidate in next_markers]
    candidates = [candidate for candidate in candidates if candidate >= 0]
    end = min(candidates) if candidates else len(source)
    return start, end, source[start:end]


def patch_client() -> None:
    """Align LineageWeave's strict client with TEPP's closed snake-case codes."""
    path = "lineageweave/tepp_project_history.py"
    source = read(path)
    source = replace_once(
        source,
        "import http.client\nimport json\n" if "import http.client\n" in source else "import json\n",
        "import http.client\nimport json\nimport re\n" if "import http.client\n" in source else "import json\nimport re\n",
        label="client regex import",
    )
    anchor = "_MAX_IDENTITY_TEXT = 256\n"
    source = replace_once(
        source,
        anchor,
        anchor + "_CODE_PATTERN = re.compile(r\"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$\")\n",
        label="client code pattern",
    )
    helper_anchor = '''def _parse_utc_timestamp(value: Any, *, name: str) -> datetime:\n'''
    helper = '''def _require_code(value: Any, *, name: str, maximum: int = 128) -> str:\n    """Return one closed lower-snake-case code."""\n    code = _require_text(value, name=name, maximum=maximum)\n    if _CODE_PATTERN.fullmatch(code) is None:\n        raise TeppProjectHistoryUnavailable(f"{name} must be lower snake_case")\n    return code\n\n\n'''
    if helper not in source:
        source = replace_once(
            source,
            helper_anchor,
            helper + helper_anchor,
            label="client code validator",
        )
    source = source.replace(
        '''"event_type_code": _require_text(\n                self.event_type_code, name="event_type_code", maximum=96\n            ),''',
        '''"event_type_code": _require_code(\n                self.event_type_code, name="event_type_code", maximum=96\n            ),''',
    )
    source = source.replace(
        '''"availability_basis": _require_text(\n                self.availability_basis, name="availability_basis", maximum=128\n            ),''',
        '''"availability_basis": _require_code(\n                self.availability_basis, name="availability_basis", maximum=128\n            ),''',
    )
    source = source.replace(
        '''event_type_code=_require_text(\n                payload.get("event_type_code"), name="event_type_code", maximum=96\n            ),''',
        '''event_type_code=_require_code(\n                payload.get("event_type_code"), name="event_type_code", maximum=96\n            ),''',
    )
    source = source.replace(
        '''availability_basis=_require_text(\n                payload.get("availability_basis"), name="availability_basis", maximum=128\n            ),''',
        '''availability_basis=_require_code(\n                payload.get("availability_basis"), name="availability_basis", maximum=128\n            ),''',
    )
    write(path, source)


def patch_backend_adapter() -> None:
    """Load a complete authorized exact-project history and call TEPP off-loop."""
    path = "backend/app/tepp_project_history.py"
    source = read(path)
    if "import asyncio\n" not in source:
        source = replace_once(
            source,
            "import hashlib\n",
            "import asyncio\nimport hashlib\n",
            label="adapter asyncio import",
        )
    if "from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL" not in source:
        source = replace_once(
            source,
            "import asyncpg\n\n",
            "import asyncpg\n\nfrom backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL\n\n",
            label="adapter eligibility import",
        )
    source = source.replace('"handoff": "operational_handoff",', '"handoff": "handoff_recorded",')
    source = source.replace(
        '"operational_handoff": "operational_handoff",',
        '"operational_handoff": "handoff_recorded",',
    )
    source = source.replace('"go_live": "operational_handoff",', '"go_live": "handoff_recorded",')
    source = source.replace(
        'availability_basis="source_post.created_at",',
        'availability_basis="source_created_at_proxy",',
    )

    start, end, _ = function_region(
        source,
        "async def _load_project_rows(",
        next_markers=("\n\nasync def project_history_for_post_ids(",),
    )
    replacement = '''async def _load_project_rows(\n    conn: asyncpg.Connection,\n    *,\n    focus_post_id: str,\n    source_post_ids: Sequence[str],\n    corporate_entity_ids: Iterable[str],\n    knowledge_cutoff: datetime,\n) -> list[Mapping[str, Any]]:\n    """Load at most 128 eligible, authorized rows for the focus post's exact project.\n\n    ``source_post_ids`` is retained for caller compatibility but is not used as\n    an authorization shortcut.  The complete timeline is selected by exact\n    project code, publication eligibility, ABAC, and knowledge cutoff.\n    """\n    _ = source_post_ids\n    authorized_entities = list(corporate_entity_ids)\n    focus = await conn.fetchrow(\n        f"""\n        select post_id, source_project_code, source_project_name\n          from source_post post\n         where post.post_id = $1::uuid\n           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}\n           and (\n               post.visibility_code = 'public'\n               or post.corporate_entity_id::text = any($2::text[])\n           )\n        """,\n        focus_post_id,\n        authorized_entities,\n    )\n    if focus is None or not str(focus["source_project_code"] or "").strip():\n        return []\n    project_key = str(focus["source_project_code"]).strip()\n    rows = await conn.fetch(\n        f"""\n        select post.post_id,\n               post.post_title,\n               post.source_stage_code,\n               post.voc_type_code,\n               post.source_project_code,\n               post.source_project_name,\n               btrim(left(source_post_search_text(post.post_body), 2000)) as post_body_excerpt,\n               post.created_at,\n               post.author_account_id::text as author_actor_id\n          from source_post post\n         where post.source_project_code = $1\n           and post.created_at <= $2\n           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}\n           and (\n               post.visibility_code = 'public'\n               or post.corporate_entity_id::text = any($3::text[])\n           )\n         order by post.created_at, post.post_id\n         limit 128\n        """,\n        project_key,\n        knowledge_cutoff,\n        authorized_entities,\n    )\n    return [dict(row) for row in rows]\n'''
    source = source[:start] + replacement + source[end:]
    source = replace_once(
        source,
        "        projection = client.project(request)\n",
        "        projection = await asyncio.to_thread(client.project, request)\n",
        label="adapter off-loop TEPP call",
    )
    write(path, source)


def patch_tests() -> None:
    """Extend RED contracts for separated event/availability clocks and handoff."""
    client_path = "tests/test_tepp_project_history.py"
    source = read(client_path).replace("source_post.created_at", "source_created_at_proxy")
    anchor = '''def test_project_history_request_rejects_future_or_non_utc_cutoffs() -> None:\n'''
    added = '''def test_project_history_request_allows_known_future_event_but_rejects_bad_basis() -> None:\n    request = _request()\n    future_event = ProjectHistoryEvent(\n        **{\n            **request.events[0].__dict__,\n            "event_time": "2026-08-21T00:00:00Z",\n            "available_at": "2026-08-18T00:00:00Z",\n        }\n    )\n    accepted = ProjectHistoryRequest(\n        **{**request.__dict__, "events": (future_event, request.events[1])}\n    )\n    wire = accepted.to_wire(now=datetime(2026, 8, 20, tzinfo=timezone.utc))\n    assert wire["events"][0]["event_time"] == "2026-08-21T00:00:00Z"\n\n    invalid_event = ProjectHistoryEvent(\n        **{**request.events[0].__dict__, "availability_basis": "source.post.created_at"}\n    )\n    invalid = ProjectHistoryRequest(\n        **{**request.__dict__, "events": (invalid_event, request.events[1])}\n    )\n    with pytest.raises(TeppProjectHistoryUnavailable):\n        invalid.to_wire(now=datetime(2026, 8, 20, tzinfo=timezone.utc))\n\n\n'''
    if added not in source:
        source = replace_once(source, anchor, added + anchor, label="client future-event test")
    write(client_path, source)

    ingestion_path = "tests/test_tepp_project_history_ingestion.py"
    source = read(ingestion_path).replace("source_post.created_at", "source_created_at_proxy")
    delivery_anchor = '''            _row(\n                "post-voc",\n                "VOC received",\n'''
    handoff = '''            _row(\n                "post-handoff",\n                "Operational handoff",\n                "handoff",\n                "2024-01-01T00:00:00Z",\n                actor_ids=("actor-operations",),\n            ),\n'''
    if handoff not in source:
        source = replace_once(
            source,
            delivery_anchor,
            handoff + delivery_anchor,
            label="ingestion handoff fixture",
        )
    source = source.replace(
        '''        "specification_changed",\n        "voc_received",\n''',
        '''        "specification_changed",\n        "handoff_recorded",\n        "voc_received",\n''',
    )
    source = source.replace(
        '''        "post-spec",\n        "post-voc",\n''',
        '''        "post-spec",\n        "post-handoff",\n        "post-voc",\n''',
    )
    source = source.replace(
        '''    assert "settings.tepp_api_key" not in source[source.index("project_history_for_post_ids"):]''',
        '''    project_history_lines = [\n        line for line in source.splitlines() if "project_history" in line\n    ]\n    assert project_history_lines\n    assert all("api_key" not in line for line in project_history_lines)''',
    )
    write(ingestion_path, source)

    component_test = "frontend/src/components/ProjectHistoryTimeline.test.tsx"
    write(component_test, read(component_test).replace("source_post.created_at", "source_created_at_proxy"))
    story = "frontend/src/components/ProjectHistoryTimeline.stories.tsx"
    write(story, read(story).replace("source_post.created_at", "source_created_at_proxy"))


def patch_main() -> None:
    """Attach one optional TEPP history to post read, post Ask, and Global Ask."""
    path = "backend/app/main.py"
    source = read(path)
    source = replace_once(
        source,
        "from datetime import datetime\n",
        "from datetime import datetime, timezone\n",
        label="main timezone import",
    )
    if "from backend.app.tepp_project_history import project_history_for_post_ids" not in source:
        source = replace_once(
            source,
            "from backend.app.post_summary_ingestion import (",
            "from backend.app.tepp_project_history import project_history_for_post_ids\nfrom backend.app.post_summary_ingestion import (",
            label="main project-history import",
        )

    endpoint = '''\n\n@app.get("/api/posts/{post_id}/project-history")\nasync def read_post_project_history(\n    post_id: str,\n    account: CurrentAccount = Depends(get_current_account),\n    pool: asyncpg.Pool = Depends(get_pool),\n) -> dict[str, Any]:\n    """Return TEPP's cutoff-safe exact-project timeline for one visible post."""\n    await _load_visible_post(post_id, account, pool)\n    async with pool.acquire() as conn:\n        return await project_history_for_post_ids(\n            conn,\n            tenant_workspace_id=str(account.user_account_id),\n            corporate_entity_ids=account.corporate_entity_ids,\n            focus_post_id=post_id,\n            source_post_ids=[post_id],\n            knowledge_cutoff=datetime.now(timezone.utc),\n            tepp_transport_url=load_settings().tepp_transport_url,\n        )\n'''
    if endpoint not in source:
        source = replace_once(
            source,
            "\n\nclass ChatRequest(BaseModel):",
            endpoint + "\n\nclass ChatRequest(BaseModel):",
            label="main project-history endpoint",
        )

    stored_old = '''        if stored is not None:\n            source_ids = [post_id]\n            source_ids.extend(cid for cid in stored["cited_post_ids"] if cid != post_id)\n            return {\n                "post_id": post_id,\n                "answer_text": stored["answer_text"],\n                "cited_post_ids": stored["cited_post_ids"],\n                "cited_posts": stored["cited_posts"],\n                "source_post_ids": source_ids,\n            }\n'''
    stored_new = '''        if stored is not None:\n            source_ids = [post_id]\n            source_ids.extend(cid for cid in stored["cited_post_ids"] if cid != post_id)\n            history = await project_history_for_post_ids(\n                conn,\n                tenant_workspace_id=str(account.user_account_id),\n                corporate_entity_ids=account.corporate_entity_ids,\n                focus_post_id=post_id,\n                source_post_ids=source_ids,\n                knowledge_cutoff=datetime.now(timezone.utc),\n                tepp_transport_url=load_settings().tepp_transport_url,\n            )\n            return {\n                "post_id": post_id,\n                "answer_text": stored["answer_text"],\n                "cited_post_ids": stored["cited_post_ids"],\n                "cited_posts": stored["cited_posts"],\n                "source_post_ids": source_ids,\n                "tepp_project_history": history["project_history"],\n                "tepp_project_history_status": history["status"],\n            }\n'''
    source = replace_once(source, stored_old, stored_new, label="stored post Ask history")

    live_old = '''    async with pool.acquire() as conn:\n        await persist_post_chat(conn, post_id, question, answer.answer_text, cited_ids)\n    return {\n        "post_id": post_id,\n        "answer_text": answer.answer_text,\n        "cited_post_ids": cited_ids,\n        "cited_posts": cited_post_summaries(sources, cited_ids),\n        "source_post_ids": [source.post_id for source in sources],\n    }\n'''
    live_new = '''    source_ids = [source.post_id for source in sources]\n    async with pool.acquire() as conn:\n        await persist_post_chat(conn, post_id, question, answer.answer_text, cited_ids)\n        history = await project_history_for_post_ids(\n            conn,\n            tenant_workspace_id=str(account.user_account_id),\n            corporate_entity_ids=account.corporate_entity_ids,\n            focus_post_id=post_id,\n            source_post_ids=source_ids,\n            knowledge_cutoff=datetime.now(timezone.utc),\n            tepp_transport_url=load_settings().tepp_transport_url,\n        )\n    return {\n        "post_id": post_id,\n        "answer_text": answer.answer_text,\n        "cited_post_ids": cited_ids,\n        "cited_posts": cited_post_summaries(sources, cited_ids),\n        "source_post_ids": source_ids,\n        "tepp_project_history": history["project_history"],\n        "tepp_project_history_status": history["status"],\n    }\n'''
    source = replace_once(source, live_old, live_new, label="live post Ask history")

    no_sources_old = '''            "cited_post_evidence": [],\n            "next_action": "No authorized source posts are available for this question.",\n'''
    no_sources_new = '''            "cited_post_evidence": [],\n            "tepp_project_history": None,\n            "tepp_project_history_status": "insufficient_project_evidence",\n            "next_action": "No authorized source posts are available for this question.",\n'''
    source = replace_once(source, no_sources_old, no_sources_new, label="empty Global Ask history")

    ask_old = '''    cited_ids = list(answer.cited_post_ids)\n    return {\n        "answer_text": answer.answer_text,\n        "cited_post_ids": cited_ids,\n        "cited_posts": cited_post_summaries(sources, cited_ids),\n        "cited_post_evidence": cited_post_evidence(sources, cited_ids),\n        "source_post_ids": [source.post_id for source in sources],\n    }\n'''
    ask_new = '''    cited_ids = list(answer.cited_post_ids)\n    source_ids = [source.post_id for source in sources]\n    focus_post_id = cited_ids[0] if cited_ids else source_ids[0]\n    async with pool.acquire() as conn:\n        history = await project_history_for_post_ids(\n            conn,\n            tenant_workspace_id=str(account.user_account_id),\n            corporate_entity_ids=account.corporate_entity_ids,\n            focus_post_id=focus_post_id,\n            source_post_ids=source_ids,\n            knowledge_cutoff=datetime.now(timezone.utc),\n            tepp_transport_url=load_settings().tepp_transport_url,\n        )\n    return {\n        "answer_text": answer.answer_text,\n        "cited_post_ids": cited_ids,\n        "cited_posts": cited_post_summaries(sources, cited_ids),\n        "cited_post_evidence": cited_post_evidence(sources, cited_ids),\n        "source_post_ids": source_ids,\n        "tepp_project_history": history["project_history"],\n        "tepp_project_history_status": history["status"],\n    }\n'''
    source = replace_once(source, ask_old, ask_new, label="Global Ask history")
    write(path, source)


def patch_api() -> None:
    """Publish the TEPP DTOs and fetch function to the Buyer frontend."""
    path = "frontend/src/api.ts"
    source = read(path)
    block = '''export interface TeppProjectHistoryEvent {\n  event_id: string;\n  event_type_code: string;\n  event_title: string;\n  event_time: string;\n  available_at: string;\n  availability_basis: string;\n  source_post_id: string;\n  evidence_text: string;\n  actor_ids: string[];\n}\n\nexport interface TeppProjectHistoryFinding {\n  finding_code: string;\n  summary: string;\n  related_event_ids: string[];\n  evidence_post_ids: string[];\n}\n\nexport interface TeppProjectHistory {\n  contract_version: number;\n  project_key: string;\n  project_name: string;\n  focus_event_id: string;\n  inference_status: "temporal_association_only";\n  participant_count: number;\n  history_span_start: string;\n  history_span_end: string;\n  events: TeppProjectHistoryEvent[];\n  findings: TeppProjectHistoryFinding[];\n}\n\nexport interface TeppProjectHistoryEnvelope {\n  status: string;\n  project_history: TeppProjectHistory | null;\n  next_action: string;\n}\n\n'''
    if block not in source:
        source = replace_once(
            source,
            "export interface ChatAnswer {",
            block + "export interface ChatAnswer {",
            label="frontend project-history DTOs",
        )
    source = source.replace(
        '''  source_post_ids: string[];\n}\n\nexport interface ChatExchange {''',
        '''  source_post_ids: string[];\n  tepp_project_history?: TeppProjectHistory | null;\n  tepp_project_history_status?: string;\n}\n\nexport interface ChatExchange {''',
        1,
    )
    source = source.replace(
        '''  cited_posts?: CitedPostRef[];\n}\n\nexport interface ChatHistory {''',
        '''  cited_posts?: CitedPostRef[];\n  tepp_project_history?: TeppProjectHistory | null;\n  tepp_project_history_status?: string;\n}\n\nexport interface ChatHistory {''',
        1,
    )
    source = source.replace(
        '''  source_post_ids: string[];\n  next_action?: string;\n}\n\nexport interface IssueTicket {''',
        '''  source_post_ids: string[];\n  tepp_project_history?: TeppProjectHistory | null;\n  tepp_project_history_status?: string;\n  next_action?: string;\n}\n\nexport interface IssueTicket {''',
        1,
    )
    fetch_block = '''export function fetchPostProjectHistory(\n  accessToken: string,\n  postId: string,\n): Promise<TeppProjectHistoryEnvelope> {\n  return backendFetch(`/api/posts/${postId}/project-history`, accessToken);\n}\n\n'''
    if fetch_block not in source:
        source = replace_once(
            source,
            "export function fetchPostChat(accessToken: string, postId: string): Promise<ChatHistory> {",
            fetch_block + "export function fetchPostChat(accessToken: string, postId: string): Promise<ChatHistory> {",
            label="frontend project-history fetch",
        )
    write(path, source)


def patch_component() -> None:
    """Use shared i18n and buyer-action copy in the timeline component."""
    write(
        "frontend/src/components/ProjectHistoryTimeline.tsx",
        '''import { useEffect, useState, type CSSProperties } from "react";\n\nimport {\n  fetchPostProjectHistory,\n  type TeppProjectHistory,\n  type TeppProjectHistoryEnvelope,\n} from "../api";\nimport { t, tf } from "../i18n";\nimport "./ProjectHistoryTimeline.css";\n\nconst EVENT_LABELS: Record<string, string> = {\n  contract_awarded: "Contract awarded",\n  specification_changed: "Specification changed",\n  delivered: "Delivered",\n  handoff_recorded: "Handoff recorded",\n  voc_received: "VOC received",\n  rebid_started: "Rebid started",\n  event_observed: "Observed project event",\n};\n\nfunction dateLabel(value: string): string {\n  const date = new Date(value);\n  if (Number.isNaN(date.valueOf())) return value;\n  const year = String(date.getUTCFullYear()).slice(-2);\n  const month = String(date.getUTCMonth() + 1).padStart(2, "0");\n  return `'${year}.${month}`;\n}\n\nexport function ProjectHistoryTimeline({\n  history,\n  onOpenPost,\n}: {\n  history: TeppProjectHistory;\n  onOpenPost: (postId: string) => void;\n}) {\n  const finding = history.findings[0];\n  const focus = history.events.find((event) => event.event_id === history.focus_event_id);\n  const listStyle = {\n    "--tepp-event-count": Math.max(1, history.events.length),\n  } as CSSProperties;\n\n  return (\n    <section className="tepp-project-history" role="region" aria-label="TEPP project history">\n      <div className="tepp-project-history__header">\n        <div>\n          <p className="section-eyebrow">{t("TEPP linked answer")}</p>\n          <h3>{t("Project event timeline")}</h3>\n          <p>{tf("{project} explicit events are ordered within the knowledge cutoff.", { project: history.project_name })}</p>\n        </div>\n        <span className="post-badge">TEPP · v{history.contract_version}</span>\n      </div>\n\n      <ol className="tepp-project-history__timeline" style={listStyle}>\n        {history.events.map((event) => {\n          const focused = event.event_id === history.focus_event_id;\n          return (\n            <li\n              key={event.event_id}\n              className={focused ? "tepp-project-history__event is-focus" : "tepp-project-history__event"}\n            >\n              <time dateTime={event.event_time}>{dateLabel(event.event_time)}</time>\n              <button\n                type="button"\n                aria-label={tf("Open evidence: {title}", { title: event.event_title })}\n                aria-current={focused ? "step" : undefined}\n                onClick={() => onOpenPost(event.source_post_id)}\n              >\n                <span className="tepp-project-history__dot" aria-hidden="true" />\n                <strong>{t(EVENT_LABELS[event.event_type_code] ?? event.event_type_code)}</strong>\n                <span>{event.event_title}</span>\n              </button>\n            </li>\n          );\n        })}\n      </ol>\n\n      <div className="tepp-project-history__detail">\n        <h4>{t("Event detail")}</h4>\n        <p>\n          {t("Current event:")} <strong>{focus?.event_title ?? t("Unknown")}</strong>\n          {" · "}{tf("{count} participants", { count: history.participant_count })}\n        </p>\n        <p>\n          <strong>{t("TEPP finding:")}</strong>{" "}\n          {finding\n            ? finding.summary\n            : t("Explicit events are ordered by time. No causal conclusion is generated.")}\n        </p>\n      </div>\n\n      <p className="tepp-project-history__boundary">\n        {t("TEPP explains only temporal associations in supplied evidence. Missing events, participants, causal relations, and psychometric scores are not generated.")}\n      </p>\n    </section>\n  );\n}\n\nexport function PostProjectHistory({\n  accessToken,\n  postId,\n  onOpenPost,\n}: {\n  accessToken: string;\n  postId: string;\n  onOpenPost: (postId: string) => void;\n}) {\n  const [envelope, setEnvelope] = useState<TeppProjectHistoryEnvelope | null>(null);\n\n  useEffect(() => {\n    let active = true;\n    setEnvelope(null);\n    fetchPostProjectHistory(accessToken, postId)\n      .then((result) => {\n        if (active) setEnvelope(result);\n      })\n      .catch(() => {\n        if (active) {\n          setEnvelope({\n            status: "tepp_unavailable",\n            project_history: null,\n            next_action: "TEPP project history is unavailable.",\n          });\n        }\n      });\n    return () => {\n      active = false;\n    };\n  }, [accessToken, postId]);\n\n  if (envelope === null) {\n    return <p className="popup-placeholder">{t("Loading TEPP project history...")}</p>;\n  }\n  if (!envelope.project_history) {\n    return (\n      <section className="popup-section tepp-project-history-status" aria-label={t("TEPP project history status")}>\n        <h3>{t("Project event timeline")}</h3>\n        <p>{t(envelope.next_action)}</p>\n      </section>\n    );\n  }\n  return <ProjectHistoryTimeline history={envelope.project_history} onOpenPost={onOpenPost} />;\n}\n''',
    )


def patch_app() -> None:
    """Render the same timeline in post read, post Ask, and Global Ask."""
    path = "frontend/src/App.tsx"
    source = read(path)
    if 'from "./components/ProjectHistoryTimeline"' not in source:
        source = replace_once(
            source,
            'import { PopupCloseButton } from "./components/PopupCloseButton";\n',
            'import { PopupCloseButton } from "./components/PopupCloseButton";\nimport { PostProjectHistory, ProjectHistoryTimeline } from "./components/ProjectHistoryTimeline";\n',
            label="App project-history component import",
        )
    old_signature = '''function ChatPanel({\n  postId,\n  accessToken,\n  nameFirstAsk,\n}: {\n  postId: string;\n  accessToken: string;\n  nameFirstAsk?: boolean;\n}) {'''
    new_signature = '''function ChatPanel({\n  postId,\n  accessToken,\n  nameFirstAsk,\n  onOpenPost,\n}: {\n  postId: string;\n  accessToken: string;\n  nameFirstAsk?: boolean;\n  onOpenPost?: (postId: string) => void;\n}) {'''
    source = replace_once(source, old_signature, new_signature, label="ChatPanel history navigation")
    source = replace_once(
        source,
        '''          cited_posts: result.cited_posts,\n        };''',
        '''          cited_posts: result.cited_posts,\n          tepp_project_history: result.tepp_project_history,\n          tepp_project_history_status: result.tepp_project_history_status,\n        };''',
        label="ChatPanel exchange history",
    )
    source = replace_once(
        source,
        '''          <p>{exchanges[0].answer_text}</p>\n          <ChatCitations''',
        '''          <p>{exchanges[0].answer_text}</p>\n          {exchanges[0].tepp_project_history ? (\n            <ProjectHistoryTimeline\n              history={exchanges[0].tepp_project_history}\n              onOpenPost={onOpenPost ?? setEvidencePostId}\n            />\n          ) : null}\n          <ChatCitations''',
        label="seeded post Ask history",
    )
    source = replace_once(
        source,
        '''          <p>{exchange.answer_text}</p>\n          <ChatCitations''',
        '''          <p>{exchange.answer_text}</p>\n          {exchange.tepp_project_history ? (\n            <ProjectHistoryTimeline\n              history={exchange.tepp_project_history}\n              onOpenPost={onOpenPost ?? setEvidencePostId}\n            />\n          ) : null}\n          <ChatCitations''',
        label="post Ask exchange history",
    )
    source = replace_once(
        source,
        '''          <p>{answer.answer_text}</p>\n          <ChatCitations''',
        '''          <p>{answer.answer_text}</p>\n          {answer.tepp_project_history ? (\n            <ProjectHistoryTimeline\n              history={answer.tepp_project_history}\n              onOpenPost={onOpenPost ?? setEvidencePostId}\n            />\n          ) : null}\n          <ChatCitations''',
        label="post Ask current history",
    )
    source = replace_once(
        source,
        '''            <RelatedPostsSection lineage={lineage} onSelectPost={onSelectPost} />\n\n            <section className="popup-section">''',
        '''            <RelatedPostsSection lineage={lineage} onSelectPost={onSelectPost} />\n\n            {onSelectPost ? (\n              <PostProjectHistory\n                accessToken={accessToken}\n                postId={postId}\n                onOpenPost={onSelectPost}\n              />\n            ) : null}\n\n            <section className="popup-section">''',
        label="post read project history",
    )
    source = replace_once(
        source,
        '''              <ChatPanel postId={postId} accessToken={accessToken} />''',
        '''              <ChatPanel\n                postId={postId}\n                accessToken={accessToken}\n                onOpenPost={onSelectPost}\n              />''',
        label="post Ask timeline navigation prop",
    )
    source = replace_once(
        source,
        '''          {answer.answer_text ? <p>{answer.answer_text}</p> : null}\n          {answer.next_action ?''',
        '''          {answer.answer_text ? <p>{answer.answer_text}</p> : null}\n          {answer.tepp_project_history ? (\n            <ProjectHistoryTimeline\n              history={answer.tepp_project_history}\n              onOpenPost={onOpenPost}\n            />\n          ) : null}\n          {answer.next_action ?''',
        label="Global Ask project history",
    )
    write(path, source)


def patch_i18n() -> None:
    """Add the new buyer-copy keys to every supported locale."""
    path = "frontend/src/i18n.ts"
    source = read(path)
    translations = {
        "ko": {
            "TEPP linked answer": "TEPP 연계 응답",
            "Project event timeline": "프로젝트 이벤트 타임라인",
            "{project} explicit events are ordered within the knowledge cutoff.": "{project}의 명시적 이벤트를 지식 기준 시각 안에서 시간순으로 연결합니다.",
            "Contract awarded": "수주",
            "Specification changed": "사양 변경",
            "Delivered": "납품",
            "Handoff recorded": "인수인계",
            "VOC received": "VOC 접수",
            "Rebid started": "재입찰",
            "Observed project event": "관측된 프로젝트 이벤트",
            "Event detail": "이벤트 상세",
            "Current event:": "현재 이벤트:",
            "{count} participants": "담당 이력 {count}명",
            "TEPP finding:": "TEPP 판단:",
            "Explicit events are ordered by time. No causal conclusion is generated.": "명시적 사건을 시간순으로 정렬했습니다. 인과 결론은 생성하지 않습니다.",
            "TEPP explains only temporal associations in supplied evidence. Missing events, participants, causal relations, and psychometric scores are not generated.": "TEPP는 제공된 증거의 시간적 연관만 설명합니다. 누락된 사건·담당자·인과관계·심리측정 점수는 생성하지 않습니다.",
            "Loading TEPP project history...": "TEPP 프로젝트 이력을 불러오는 중입니다...",
            "TEPP project history status": "TEPP 프로젝트 이력 상태",
        },
        "zh": {
            "TEPP linked answer": "TEPP 关联回答",
            "Project event timeline": "项目事件时间线",
            "{project} explicit events are ordered within the knowledge cutoff.": "在知识截止时间内按时间顺序排列 {project} 的明确事件。",
            "Contract awarded": "合同授予",
            "Specification changed": "规格变更",
            "Delivered": "交付",
            "Handoff recorded": "交接记录",
            "VOC received": "收到 VOC",
            "Rebid started": "重新投标准备",
            "Observed project event": "已观测项目事件",
            "Event detail": "事件详情",
            "Current event:": "当前事件：",
            "{count} participants": "{count} 名参与者",
            "TEPP finding:": "TEPP 发现：",
            "Explicit events are ordered by time. No causal conclusion is generated.": "明确事件已按时间排序，不生成因果结论。",
            "TEPP explains only temporal associations in supplied evidence. Missing events, participants, causal relations, and psychometric scores are not generated.": "TEPP 仅说明所提供证据中的时间关联，不生成缺失事件、参与者、因果关系或心理测量分数。",
            "Loading TEPP project history...": "正在加载 TEPP 项目历史...",
            "TEPP project history status": "TEPP 项目历史状态",
        },
        "ja": {
            "TEPP linked answer": "TEPP 連携回答",
            "Project event timeline": "プロジェクトイベントのタイムライン",
            "{project} explicit events are ordered within the knowledge cutoff.": "{project} の明示的なイベントを知識カットオフ内で時系列に並べます。",
            "Contract awarded": "受注",
            "Specification changed": "仕様変更",
            "Delivered": "納品",
            "Handoff recorded": "引継ぎ記録",
            "VOC received": "VOC 受付",
            "Rebid started": "再入札開始",
            "Observed project event": "観測済みプロジェクトイベント",
            "Event detail": "イベント詳細",
            "Current event:": "現在のイベント：",
            "{count} participants": "参加者 {count} 名",
            "TEPP finding:": "TEPP 所見：",
            "Explicit events are ordered by time. No causal conclusion is generated.": "明示的なイベントを時系列に並べました。因果結論は生成しません。",
            "TEPP explains only temporal associations in supplied evidence. Missing events, participants, causal relations, and psychometric scores are not generated.": "TEPP は提示された証拠の時間的関連のみを説明し、欠落したイベント・参加者・因果関係・心理測定スコアを生成しません。",
            "Loading TEPP project history...": "TEPP プロジェクト履歴を読み込み中...",
            "TEPP project history status": "TEPP プロジェクト履歴の状態",
        },
        "vi": {
            "TEPP linked answer": "Phản hồi liên kết TEPP",
            "Project event timeline": "Dòng thời gian sự kiện dự án",
            "{project} explicit events are ordered within the knowledge cutoff.": "Các sự kiện rõ ràng của {project} được sắp xếp theo thời gian trong giới hạn tri thức.",
            "Contract awarded": "Trao hợp đồng",
            "Specification changed": "Thay đổi đặc tả",
            "Delivered": "Đã bàn giao",
            "Handoff recorded": "Ghi nhận chuyển giao",
            "VOC received": "Đã nhận VOC",
            "Rebid started": "Bắt đầu đấu thầu lại",
            "Observed project event": "Sự kiện dự án đã quan sát",
            "Event detail": "Chi tiết sự kiện",
            "Current event:": "Sự kiện hiện tại:",
            "{count} participants": "{count} người tham gia",
            "TEPP finding:": "Phát hiện TEPP:",
            "Explicit events are ordered by time. No causal conclusion is generated.": "Các sự kiện rõ ràng được sắp xếp theo thời gian. Không tạo kết luận nhân quả.",
            "TEPP explains only temporal associations in supplied evidence. Missing events, participants, causal relations, and psychometric scores are not generated.": "TEPP chỉ giải thích liên hệ thời gian trong bằng chứng được cung cấp; không tạo sự kiện, người tham gia, quan hệ nhân quả hoặc điểm đo lường tâm lý còn thiếu.",
            "Loading TEPP project history...": "Đang tải lịch sử dự án TEPP...",
            "TEPP project history status": "Trạng thái lịch sử dự án TEPP",
        },
    }
    for locale, mapping in translations.items():
        anchor = f"  {locale}: {{\n"
        if f'    "TEPP linked answer":' in source[source.index(anchor):]:
            continue
        lines = [f'    {repr(key)}: {repr(value)},' for key, value in mapping.items()]
        # TypeScript accepts JSON-style double-quoted string keys and values;
        # repr is normalized below to avoid apostrophe escaping differences.
        block = "\n".join(lines).replace("'", '"') + "\n"
        source = replace_once(
            source,
            anchor,
            anchor + block,
            label=f"{locale} project-history translations",
        )
    write(path, source)


def patch_docs_and_version() -> None:
    """Record the bounded architecture decision and release delta."""
    env_path = ".env.example"
    env = read(env_path)
    note = '''\n# TEPP project-history calls use the HTTPS service URL below without forwarding\n# browser, review, provider, or database credentials. TEPP publishes\n# /v1/project-histories beside /v1/analysis-runs.\n# TEPP_TRANSPORT_URL=https://tepp.example.com/v1/analysis-runs\n'''
    if note not in env:
        write(env_path, env + note)

    write(
        "CHANGELOG.d/2.18.0-tepp-project-history.md",
        """# 2.18.0 — TEPP project-history Buyer evidence\n\n- Post reading, Global Ask, and post Ask render one TEPP-validated exact-project timeline.\n- Every event returns to an authorized source post and preserves evidence availability at the knowledge cutoff.\n- Event time and evidence availability are distinct; a known future milestone is allowed without admitting evidence learned after the cutoff.\n- TEPP findings remain temporal associations and never become causal conclusions, theta, confidence, or completed psychometric results.\n""",
    )

    adr_dir = ROOT / "docs/adr"
    existing = [
        int(path.name[:4])
        for path in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")
        if path.name[:4].isdigit()
    ]
    number = max(existing, default=0) + 1
    adr_path = f"docs/adr/{number:04d}-tepp-project-history-buyer-evidence.md"
    if not (ROOT / adr_path).exists():
        write(
            adr_path,
            f"""# ADR {number:04d}: TEPP-owned project-history evidence on Buyer surfaces\n\n## Status\n\nAccepted on the stacked feature branch; release remains gated by the TEPP and LineageWeave predecessor PRs.\n\n## Context\n\nLineageWeave owns authorization, project identity, source-post evidence, and Buyer navigation. TEPP owns temporal validation and projection. Reimplementing temporal reasoning in LineageWeave would create competing authority, while forwarding browser or provider credentials would breach the modular service boundary.\n\n## Decision\n\nLineageWeave selects up to 128 publication-eligible, ABAC-visible records with the exact persisted `source_project_code` and `created_at <= knowledge_cutoff`. It sends event time, evidence availability, an explicit availability basis, source post, evidence excerpt, and opaque participant IDs over a credential-free HTTPS contract.\n\nTEPP admits evidence when `available_at <= knowledge_cutoff`; `event_time` may be later when a future commitment was already known. TEPP preserves the supplied evidence, orders events deterministically, derives participant count, and returns only `temporal_association_only` findings. Each finding cites the focus event and exact source posts and explicitly denies a causal conclusion.\n\nThe same projection is exposed by post reading, post-scoped Ask, and Global Ask. TEPP failure returns an optional typed unavailable state and does not erase the underlying authorized answer.\n\n## Consequences\n\n- Buyers can inspect contract award, specification change, delivery or handoff, VOC, and rebid evidence in one timeline.\n- A timeline event navigates to its exact source post.\n- Missing events, participants, causal relations, confidence, theta, and psychometric completion remain missing.\n- TEPP performs blocking HTTP work off the async event loop.\n""",
        )

    pyproject = "pyproject.toml"
    py = read(pyproject)
    py = py.replace('version = "2.17.0"', 'version = "2.18.0"', 1)
    write(pyproject, py)

    package_path = "frontend/package.json"
    package = read(package_path)
    package = package.replace('"version": "2.17.0"', '"version": "2.18.0"', 1)
    write(package_path, package)


def main() -> None:
    """Apply and enumerate the complete production delta."""
    patch_client()
    patch_backend_adapter()
    patch_tests()
    patch_main()
    patch_api()
    patch_component()
    patch_app()
    patch_i18n()
    patch_docs_and_version()

    paths = [
        ".env.example",
        "CHANGELOG.d/2.18.0-tepp-project-history.md",
        "backend/app/main.py",
        "backend/app/tepp_project_history.py",
        "frontend/package.json",
        "frontend/src/App.tsx",
        "frontend/src/api.ts",
        "frontend/src/components/ProjectHistoryTimeline.css",
        "frontend/src/components/ProjectHistoryTimeline.stories.tsx",
        "frontend/src/components/ProjectHistoryTimeline.test.tsx",
        "frontend/src/components/ProjectHistoryTimeline.tsx",
        "frontend/src/i18n.ts",
        "lineageweave/tepp_project_history.py",
        "pyproject.toml",
        "tests/test_tepp_project_history.py",
        "tests/test_tepp_project_history_ingestion.py",
    ]
    paths.extend(
        str(path.relative_to(ROOT))
        for path in (ROOT / "docs/adr").glob("*-tepp-project-history-buyer-evidence.md")
    )
    write(".implementation_282_paths", "\n".join(paths) + "\n")


if __name__ == "__main__":
    main()
