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


def main() -> None:
    """Make interpolated eligibility SQL executable and remove a stale import."""

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


if __name__ == "__main__":
    main()
