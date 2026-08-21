"""Repair generated-code details after the bounded Ask transform."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    """Replace one exact generated fragment."""

    file_path = ROOT / path
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one generated anchor in {path}, found {count}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_new(path: str, content: str) -> None:
    """Create one migration artifact and reject accidental overwrite."""

    file_path = ROOT / path
    if file_path.exists():
        raise RuntimeError(f"refusing to overwrite existing {path}")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content.strip() + "\n", encoding="utf-8")


def repair_sql_interpolation() -> None:
    """Make schema-owned eligibility fragments interpolate before execution."""

    replace_once(
        "backend/app/post_chat_ingestion.py",
        """        candidate_rows = await conn.fetch(
            """
            select post_id, matched_in
""",
        """        candidate_rows = await conn.fetch(
            f"""
            select post_id, matched_in
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """    rows = await conn.fetch(
        """
        select post_id, post_title, post_body, visibility_code, corporate_entity_id,
               created_at,
""",
        """    rows = await conn.fetch(
        f"""
        select post_id, post_title, post_body, visibility_code, corporate_entity_id,
               created_at,
""",
    )
    replace_once(
        "backend/app/main.py",
        "    cited_post_evidence,\n    cited_post_summaries,\n",
        "    cited_post_evidence,\n",
    )


def add_exact_post_chat_cutoff() -> None:
    """Persist the retrieval cutoff instead of reconstructing it from write time."""

    write_new(
        "migrations/0053_post_chat_knowledge_cutoff.sql",
        """
alter table post_chat_result
    add column if not exists knowledge_cutoff timestamptz;

update post_chat_result
   set knowledge_cutoff = computed_at
 where knowledge_cutoff is null;

alter table post_chat_result
    alter column knowledge_cutoff set default now(),
    alter column knowledge_cutoff set not null;

do $$
begin
    if not exists (
        select 1
          from pg_constraint
         where conname = 'post_chat_result_knowledge_cutoff_check'
           and conrelid = 'post_chat_result'::regclass
    ) then
        alter table post_chat_result
            add constraint post_chat_result_knowledge_cutoff_check
            check (knowledge_cutoff <= computed_at);
    end if;
end
$$;

comment on column post_chat_result.knowledge_cutoff is
    'Maximum source availability time used to compute this persisted answer.';
""",
    )
    write_new(
        "migrations/rollback/0053_post_chat_knowledge_cutoff.sql",
        """
alter table post_chat_result
    drop constraint if exists post_chat_result_knowledge_cutoff_check;

alter table post_chat_result
    drop column if exists knowledge_cutoff;
""",
    )
    replace_once(
        "docker/postgres-init/migrate.sh",
        "        0051_*|0052_*) ;;\n",
        "        0051_*|0052_*|0053_*) ;;\n",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        '        "select question_text, answer_text, computed_at from post_chat_result "\n',
        '        "select question_text, answer_text, knowledge_cutoff from post_chat_result "\n',
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        '        "_knowledge_cutoff": header.get("computed_at"),\n',
        '        "_knowledge_cutoff": header.get("knowledge_cutoff"),\n',
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """    cited_post_ids: list[str] | tuple[str, ...],
) -> dict[str, Any]:
""",
        """    cited_post_ids: list[str] | tuple[str, ...],
    *,
    knowledge_cutoff: datetime | None = None,
) -> dict[str, Any]:
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """    if not norm:
        raise ValueError("question is empty after normalize")
    await conn.execute(
""",
        """    if not norm:
        raise ValueError("question is empty after normalize")
    cutoff = _ask_cutoff(knowledge_cutoff)
    await conn.execute(
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """        "insert into post_chat_result (post_id, question_norm, question_text, answer_text) "
        "values ($1, $2, $3, $4)",
        post_id,
        norm,
        question.strip(),
        answer_text,
""",
        """        "insert into post_chat_result "
        "(post_id, question_norm, question_text, answer_text, knowledge_cutoff) "
        "values ($1, $2, $3, $4, $5)",
        post_id,
        norm,
        question.strip(),
        answer_text,
        cutoff,
""",
    )
    replace_once(
        "backend/app/main.py",
        """        await persist_post_chat(conn, post_id, question, answer.answer_text, cited_ids)
        answer_evidence = await read_authorized_ask_evidence(
""",
        """        await persist_post_chat(
            conn,
            post_id,
            question,
            answer.answer_text,
            cited_ids,
            knowledge_cutoff=knowledge_cutoff,
        )
        answer_evidence = await read_authorized_ask_evidence(
""",
    )


def harden_ask_projection() -> None:
    """Canonicalize untrusted IDs and bound public project projection sizes."""

    replace_once(
        "backend/app/ask_project_history.py",
        "from typing import Any, Protocol\n",
        "from typing import Any, Protocol\nfrom uuid import UUID\n",
    )
    replace_once(
        "backend/app/ask_project_history.py",
        """    citations = tuple(dict.fromkeys(str(value) for value in cited_post_ids if str(value)))
    if len(citations) > maximum_citations:
""",
        """    try:
        citations = tuple(
            dict.fromkeys(
                str(UUID(str(value))) for value in cited_post_ids if str(value).strip()
            )
        )
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("citation identities must be UUIDs") from exc
    if len(citations) > maximum_citations:
""",
    )
    replace_once(
        "backend/app/ask_project_history.py",
        """    cutoff = ask_knowledge_cutoff(knowledge_cutoff)
    cutoff_text = _cutoff_text(cutoff)
""",
        """    if maximum_projects < 0 or maximum_projects > ASK_PROJECT_LIMIT:
        raise ValueError("project count is outside the supported bound")
    cutoff = ask_knowledge_cutoff(knowledge_cutoff)
    cutoff_text = _cutoff_text(cutoff)
""",
    )


def harden_frontend_async_state() -> None:
    """Ignore stale timeline fetches and retry only the intended session conflict."""

    replace_once(
        "frontend/src/components/AskProjectHistoryLinks.tsx",
        'import { useEffect, useId, useState } from "react";\n',
        'import { useEffect, useId, useRef, useState } from "react";\n',
    )
    replace_once(
        "frontend/src/components/AskProjectHistoryLinks.tsx",
        """  const [projection, setProjection] = useState<ProjectHistoryProjection | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
""",
        """  const [projection, setProjection] = useState<ProjectHistoryProjection | null>(null);
  const [error, setError] = useState(false);
  const requestGeneration = useRef(0);

  useEffect(() => {
    requestGeneration.current += 1;
""",
    )
    replace_once(
        "frontend/src/components/AskProjectHistoryLinks.tsx",
        """    setLoading(true);
    setError(false);
    fetchProjectHistory(
""",
        """    setLoading(true);
    setError(false);
    const generation = ++requestGeneration.current;
    fetchProjectHistory(
""",
    )
    replace_once(
        "frontend/src/components/AskProjectHistoryLinks.tsx",
        """      .then((result) => {
        setProjection(result);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
""",
        """      .then((result) => {
        if (generation !== requestGeneration.current) return;
        setProjection(result);
        setLoading(false);
      })
      .catch(() => {
        if (generation !== requestGeneration.current) return;
        setError(true);
        setLoading(false);
      });
""",
    )
    replace_once(
        "frontend/src/App.tsx",
        "if (err instanceof BackendError && err.status === 409 && sessionId) {",
        """if (
        err instanceof BackendError &&
        err.status === 409 &&
        sessionId &&
        err.message.toLowerCase().includes("start a new session")
      ) {""",
    )


def main() -> None:
    """Repair SQL, exact cutoffs, hostile IDs, and asynchronous UI state."""

    repair_sql_interpolation()
    add_exact_post_chat_cutoff()
    harden_ask_projection()
    harden_frontend_async_state()


if __name__ == "__main__":
    main()
