"""Late Demo public post is the ADR 0016 own-corp cutoff counter-example."""

from datetime import datetime, timezone
from inspect import getsource
from pathlib import Path

from scripts.seed_demo_data import (
    DEMO_ANALYSIS_RUN_KNOWLEDGE_CUTOFF,
    DEMO_PUBLIC_POST_CREATED_AT,
    DEMO_PUBLIC_POST_TITLE,
    LATE_DEMO_PUBLIC_POST_BODY,
    LATE_DEMO_PUBLIC_POST_CREATED_AT,
    LATE_DEMO_PUBLIC_POST_TITLE,
    seed,
    seed_late_demo_public_post,
    tepp_accepted_seed_request,
    tepp_seed_outcome,
    tepp_seed_request,
    _ensure_demo_source_snapshot_members,
    _seed_demo_run_reconstruction,
)


def _parse_seed_clock(value: str) -> datetime:
    """Parse a seeded ISO-8601 Z clock as UTC."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class _LateDemoCursor:
    """Drive ``seed_late_demo_public_post`` without a live database."""

    def __init__(self, existing: bool = False) -> None:
        self.existing = existing
        self.statements: list[str] = []
        self.params: list[object] = []

    def execute(self, sql: str, params=None) -> None:
        self.statements.append(" ".join(sql.split()))
        self.params.append(params)

    def fetchone(self):
        last = self.statements[-1]
        if last.lstrip().startswith("select") and "from source_post" in last:
            return ("late-demo-id",) if self.existing else None
        return None


def test_january_12_run_lists_demo_public_not_late_demo() -> None:
    """ADR 0016 ``created_at <= knowledge_cutoff`` keeps Demo public, drops Late Demo."""
    cutoff = _parse_seed_clock(DEMO_ANALYSIS_RUN_KNOWLEDGE_CUTOFF)
    listed = {
        title: _parse_seed_clock(created_at) <= cutoff
        for title, created_at in (
            (DEMO_PUBLIC_POST_TITLE, DEMO_PUBLIC_POST_CREATED_AT),
            (LATE_DEMO_PUBLIC_POST_TITLE, LATE_DEMO_PUBLIC_POST_CREATED_AT),
        )
    }
    assert cutoff == datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)
    assert listed[DEMO_PUBLIC_POST_TITLE] is True
    assert listed[LATE_DEMO_PUBLIC_POST_TITLE] is False


def test_listing_still_uses_created_at_not_a_second_cutoff() -> None:
    """Visible-post SQL stays the ADR 0016 created_at gate on every scope."""
    listing = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "app"
        / "analysis_run_ingestion.py"
    ).read_text(encoding="utf-8")
    start = listing.index("async def fetch_visible_scope_posts")
    end = listing.index("\nclass AnalysisRunCreateError")
    listing_fn = listing[start:end]
    assert listing_fn.count("created_at <= $") == 4
    assert "LATE_DEMO" not in listing_fn


def test_reconstruction_seed_uses_the_january_12_cutoff() -> None:
    """Run reconstruction persists only posts known at the same analysis clock."""
    source = getsource(_seed_demo_run_reconstruction)
    assert "created_at <= %s" in source
    assert "DEMO_ANALYSIS_RUN_KNOWLEDGE_CUTOFF" in source
    assert LATE_DEMO_PUBLIC_POST_TITLE not in source


def test_snapshot_members_exclude_late_demo_created_at() -> None:
    """Frozen snapshot membership uses created_at before Late Demo exists."""
    source = getsource(_ensure_demo_source_snapshot_members)
    assert "created_at <= '2026-01-12T00:00:00Z'" in source
    late = _parse_seed_clock(LATE_DEMO_PUBLIC_POST_CREATED_AT)
    snapshot_max = datetime(2026, 1, 12, tzinfo=timezone.utc)
    assert late > snapshot_max


def test_seed_late_demo_public_post_inserts_after_cutoff() -> None:
    """Persist writes the own-corp public counter-example dated 2026-01-13."""
    cursor = _LateDemoCursor()
    seed_late_demo_public_post(cursor, "account-1", "corp-1", "pu-1")
    inserts = [
        (sql, params)
        for sql, params in zip(cursor.statements, cursor.params, strict=True)
        if "insert into source_post" in sql
    ]
    assert inserts, "missing Late Demo must be inserted"
    sql, params = inserts[0]
    assert params is not None
    assert LATE_DEMO_PUBLIC_POST_TITLE in params
    assert LATE_DEMO_PUBLIC_POST_BODY in params
    assert LATE_DEMO_PUBLIC_POST_CREATED_AT in params
    assert params.count(LATE_DEMO_PUBLIC_POST_CREATED_AT) == 2
    assert "public" in sql
    assert "theta" not in sql.lower()
    assert not any(
        isinstance(value, str) and ("theta" in value.lower() or "θ" in value)
        for value in params
    )


def test_seed_late_demo_public_post_skips_when_already_present() -> None:
    """Re-seed must not invent a second Late Demo row."""
    cursor = _LateDemoCursor(existing=True)
    seed_late_demo_public_post(cursor, "account-1", "corp-1", "pu-1")
    assert not any("insert into source_post" in sql for sql in cursor.statements)


def test_seed_calls_late_demo_before_analysis_runs() -> None:
    """``seed()`` writes Late Demo, then lineage/TEPP runs on the January 12 clock."""
    source = getsource(seed)
    late_at = source.index("seed_late_demo_public_post(")
    lineage_at = source.index("_seed_demo_analysis_run(")
    tepp_at = source.index("_seed_demo_tepp_run(")
    assert late_at < lineage_at < tepp_at
    helper = getsource(seed_late_demo_public_post)
    insert_sql = helper[helper.index("insert into source_post") :]
    assert "created_at <= " not in insert_sql
    assert "theta" not in insert_sql.lower()


def test_tepp_seed_keeps_the_same_january_12_cutoff() -> None:
    """Late Demo does not fork TEPP arithmetic or stamp Succeeded."""
    request = tepp_seed_request()
    accepted = tepp_accepted_seed_request()
    assert request.knowledge_cutoff == DEMO_ANALYSIS_RUN_KNOWLEDGE_CUTOFF
    assert accepted.knowledge_cutoff == DEMO_ANALYSIS_RUN_KNOWLEDGE_CUTOFF
    status, failure = tepp_seed_outcome()
    assert status == "analysis_status_failed"
    assert failure == "tepp_not_available"
