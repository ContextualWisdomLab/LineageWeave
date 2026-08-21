"""Harden generated post-Ask persistence against database clock skew."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    """Replace one exact generated persistence fragment."""

    file_path = ROOT / path
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one cutoff anchor in {path}, found {count}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    """Write computed and cutoff clocks from one monotonic application decision."""

    replace_once(
        "backend/app/post_chat_ingestion.py",
        """    cutoff = _ask_cutoff(knowledge_cutoff)
    await conn.execute(
        "delete from post_chat_result where post_id = $1 and question_norm = $2",
""",
        """    cutoff = _ask_cutoff(knowledge_cutoff)
    computed_at = max(datetime.now(timezone.utc), cutoff)
    await conn.execute(
        "delete from post_chat_result where post_id = $1 and question_norm = $2",
""",
    )
    replace_once(
        "backend/app/post_chat_ingestion.py",
        """        "insert into post_chat_result "
        "(post_id, question_norm, question_text, answer_text, knowledge_cutoff) "
        "values ($1, $2, $3, $4, $5)",
        post_id,
        norm,
        question.strip(),
        answer_text,
        cutoff,
""",
        """        "insert into post_chat_result "
        "(post_id, question_norm, question_text, answer_text, "
        "computed_at, knowledge_cutoff) "
        "values ($1, $2, $3, $4, $5, $6)",
        post_id,
        norm,
        question.strip(),
        answer_text,
        computed_at,
        cutoff,
""",
    )


if __name__ == "__main__":
    main()
