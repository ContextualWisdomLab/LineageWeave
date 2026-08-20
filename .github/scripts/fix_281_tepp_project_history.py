"""Apply the bounded TEPP project-history buyer-surface integration for PR 281."""

from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    """Replace one exact anchor or accept an already-applied replacement."""
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one integration anchor, found {text.count(old)}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_api() -> None:
    """Add the public project-history response types and GET client."""
    types_anchor = """export interface IssueTicket {
"""
    types = """export interface TeppProjectHistoryEvent {
  event_id: string;
  event_type_code: string;
  event_title: string;
  occurred_at: string;
  available_at: string;
  availability_basis_code: string;
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

export interface TeppProjectHistoryProjection {
  contract_version: 1;
  project_key: string;
  project_name: string;
  focus_event_id: string;
  history_span_start: string;
  history_span_end: string;
  participant_count: number;
  inference_status: "temporal_association_only";
  events: TeppProjectHistoryEvent[];
  findings: TeppProjectHistoryFinding[];
}

export interface IssueTicket {
"""
    replace_once("frontend/src/api.ts", types_anchor, types)

    function_anchor = """export function fetchPostContent(accessToken: string, postId: string): Promise<PostContentResponse> {
"""
    function = """export function fetchTeppProjectHistory(
  accessToken: string,
  postId: string,
  knowledgeCutoff?: string,
): Promise<TeppProjectHistoryProjection> {
  const query = knowledgeCutoff
    ? `?knowledge_cutoff=${encodeURIComponent(knowledgeCutoff)}`
    : "";
  return backendFetch<TeppProjectHistoryProjection>(
    `/api/posts/${postId}/project-history${query}`,
    accessToken,
  );
}

export function fetchPostContent(accessToken: string, postId: string): Promise<PostContentResponse> {
"""
    replace_once("frontend/src/api.ts", function_anchor, function)


def patch_app() -> None:
    """Place the shared timeline on document, post-Ask, and Global Ask surfaces."""
    import_anchor = 'import { CutoffKnownBody } from "./components/CutoffKnownBody";\n'
    import_line = (
        'import { CutoffKnownBody } from "./components/CutoffKnownBody";\n'
        'import { TeppProjectHistoryPanel } from "./components/TeppProjectHistory";\n'
    )
    replace_once("frontend/src/App.tsx", import_anchor, import_line)

    post_anchor = """            </section>
            {(post.source_stage_code ||
"""
    post_panel = """            </section>
            <TeppProjectHistoryPanel
              accessToken={accessToken}
              postId={postId}
              knowledgeCutoff={knowledgeCutoff ?? undefined}
              onOpenPost={(evidencePostId) => onSelectPost?.(evidencePostId)}
            />
            {(post.source_stage_code ||
"""
    replace_once("frontend/src/App.tsx", post_anchor, post_panel)

    ask_state_anchor = """  const [asking, setAsking] = useState(false);

  async function handleAsk() {
"""
    ask_state = """  const [asking, setAsking] = useState(false);
  const timelinePostId =
    answer?.cited_posts?.[0]?.post_id ?? answer?.cited_post_ids[0] ?? null;

  async function handleAsk() {
"""
    replace_once("frontend/src/App.tsx", ask_state_anchor, ask_state)

    ask_answer_anchor = """          {answer.next_action ? <p className="post-meta">{t(answer.next_action)}</p> : null}
          {answer.cited_posts && answer.cited_posts.length > 0 && (
"""
    ask_answer = """          {answer.next_action ? <p className="post-meta">{t(answer.next_action)}</p> : null}
          {timelinePostId ? (
            <TeppProjectHistoryPanel
              accessToken={accessToken}
              postId={timelinePostId}
              onOpenPost={onOpenPost}
            />
          ) : null}
          {answer.cited_posts && answer.cited_posts.length > 0 && (
"""
    replace_once("frontend/src/App.tsx", ask_answer_anchor, ask_answer)


def patch_backend() -> None:
    """Expose an authorized, no-local-substitute TEPP project-history endpoint."""
    replace_once(
        "backend/app/main.py",
        "from datetime import datetime\n",
        "from datetime import datetime, timezone\n",
    )

    client_import_anchor = "from lineageweave.http_client import HttpClientError\n"
    client_imports = """from lineageweave.http_client import HttpClientError
from lineageweave.tepp_project_history import (
    PROJECT_HISTORY_PATH,
    TeppProjectHistoryNotAvailable,
    configured_tepp_project_history_client,
)
"""
    replace_once("backend/app/main.py", client_import_anchor, client_imports)

    builder_import_anchor = "from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL\n"
    builder_imports = """from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from backend.app.tepp_project_history import (
    build_project_history_request,
    fetch_project_history_rows,
)
"""
    replace_once("backend/app/main.py", builder_import_anchor, builder_imports)

    helper_anchor = """def _post_evaluation_client():
"""
    helper = """def _tepp_project_history_client():
    \"\"\"Build the credential-free TEPP project-history channel or fail closed.\"\"\"
    configured = load_settings().tepp_transport_url.strip()
    if configured.endswith("/v1/analysis-runs"):
        configured = configured[: -len("/v1/analysis-runs")] + PROJECT_HISTORY_PATH
    elif configured and not configured.endswith(PROJECT_HISTORY_PATH):
        configured = ""
    return configured_tepp_project_history_client(configured)


def _post_evaluation_client():
"""
    replace_once("backend/app/main.py", helper_anchor, helper)

    endpoint_anchor = """@app.get("/api/posts/{post_id}/content")
async def read_post_content(
"""
    endpoint = """@app.get("/api/posts/{post_id}/project-history")
async def read_tepp_project_history(
    post_id: str,
    knowledge_cutoff: str | None = Query(None, max_length=64),
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    \"\"\"Return TEPP's cutoff-safe project timeline for one visible post.

    LineageWeave selects only authorized source evidence. TEPP owns temporal
    validation and coded associations. Missing TEPP returns 503; this endpoint
    never fabricates a local psychometric or causal substitute.
    \"\"\"
    _require_post_read(account)
    if knowledge_cutoff is None:
        cutoff = datetime.now(timezone.utc)
    else:
        try:
            cutoff = parse_as_of_clock(knowledge_cutoff)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "knowledge_cutoff must be an ISO-8601 timestamp.",
            ) from exc
    async with pool.acquire() as conn:
        focus = await conn.fetchrow(
            "select post_id, visibility_code, corporate_entity_id "
            f"from source_post where post_id = $1 and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}",
            post_id,
        )
        if focus is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "post not found")
        if not _can_see_post(account, focus):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized to view this post")
        rows = await fetch_project_history_rows(
            conn,
            focus_post_id=post_id,
            knowledge_cutoff=cutoff,
            can_see=lambda row: _can_see_post(account, row),
        )
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project history evidence not found")
    try:
        request = build_project_history_request(
            rows,
            focus_post_id=post_id,
            tenant_workspace_id=str(focus["corporate_entity_id"]),
            knowledge_cutoff=cutoff,
        )
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "visible project evidence does not satisfy the TEPP request contract.",
        ) from exc
    client = _tepp_project_history_client()
    if not client.available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "TEPP project history is not configured; no local substitute was invented.",
        )
    try:
        projection = await asyncio.to_thread(client.project, request)
    except (TeppProjectHistoryNotAvailable, ValueError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "TEPP project history is unavailable or failed contract validation.",
        ) from exc
    return projection.to_json()


@app.get("/api/posts/{post_id}/content")
async def read_post_content(
"""
    replace_once("backend/app/main.py", endpoint_anchor, endpoint)


def main() -> None:
    """Apply the exact bounded integration."""
    patch_api()
    patch_app()
    patch_backend()


if __name__ == "__main__":
    main()
