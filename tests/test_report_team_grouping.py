"""Synthetic checks for N:N team period-report grouping."""

from backend.app.report_ingestion import GROUPING_KINDS, _groups_from_rows, grouping_value


def _row(
    post_id: str,
    team_id: str,
    category: int,
    project_id: str = "project-a",
) -> dict[str, object]:
    return {
        "post_id": post_id,
        "team_id": team_id,
        "secondary_grouping_key": project_id,
        "criterion_code": "criterion_1",
        "response_category": category,
    }


def test_team_grouping_preserves_multiple_membership_without_intra_group_duplicates():
    rows = [
        _row("post-1", "team-a", 1),
        _row("post-1", "team-b", 1),
        _row("post-2", "team-a", 2),
        _row("post-3", "team-b", 2),
    ]

    groups = _groups_from_rows("team", rows)

    assert "team" in GROUPING_KINDS
    assert grouping_value("team", rows[0]) == "team-a"
    assert list(groups["team-a"][0]) == ["post-1", "post-2"]
    assert list(groups["team-b"][0]) == ["post-1", "post-3"]


def test_project_grouping_uses_persisted_secondary_key():
    rows = [
        _row("post-1", "team-a", 1, "project-a"),
        _row("post-2", "team-a", 2, "project-a"),
        _row("post-3", "team-b", 1, "project-b"),
        _row("post-4", "team-b", 2, "project-b"),
    ]

    groups = _groups_from_rows("project", rows)

    assert "project" in GROUPING_KINDS
    assert list(groups["project-a"][0]) == ["post-1", "post-2"]
    assert list(groups["project-b"][0]) == ["post-3", "post-4"]
