"""Scheduled newspaper editions consume ranks and Orgmetra. No invented theta."""

from lineageweave.newspaper_edition import (
    WEEK_EMPTY_NEXT_ACTION,
    SeedOrgmetraClient,
    assemble_newspaper_edition,
    edition_payload,
    render_newspaper_html,
)
from lineageweave.orgmetra_client import ORGMETRA_UNAVAILABLE_NEXT_ACTION, NullOrgmetraClient, OrgmetraUnit


def test_missing_orgmetra_fail_closes_without_invented_sections() -> None:
    edition = assemble_newspaper_edition(
        kind="week",
        period_code="2026-W02",
        orgmetra=NullOrgmetraClient(),
        ranked_titles_by_unit={("corporate", "corp-1"): ("Public post",)},
    )
    assert edition.sections == ()
    assert edition.empty_next_action == ORGMETRA_UNAVAILABLE_NEXT_ACTION
    assert "θ" not in render_newspaper_html(edition)


def test_missing_scores_fail_close_the_week_newspaper() -> None:
    orgmetra = SeedOrgmetraClient([OrgmetraUnit("corporate", "corp-1", "Demo Corp")])
    edition = assemble_newspaper_edition(
        kind="week",
        period_code="2026-W02",
        orgmetra=orgmetra,
        ranked_titles_by_unit={},
    )
    assert edition.empty_next_action == WEEK_EMPTY_NEXT_ACTION
    html = render_newspaper_html(edition)
    assert WEEK_EMPTY_NEXT_ACTION in html
    assert "Public post" not in html


def test_consumed_titles_fill_orgmetra_sections_without_theta() -> None:
    orgmetra = SeedOrgmetraClient(
        [
            OrgmetraUnit("corporate", "corp-1", "Demo Corp"),
            OrgmetraUnit("process_unit", "pu-1", "Demo Lineage PU"),
        ]
    )
    edition = assemble_newspaper_edition(
        kind="week",
        period_code="2026-W02",
        orgmetra=orgmetra,
        ranked_titles_by_unit={
            ("corporate", "corp-1"): ("Public post",),
            ("process_unit", "pu-1"): ("Public post",),
        },
    )
    assert edition.empty_next_action is None
    payload = edition_payload(edition)
    corporate = next(section for section in payload["sections"] if section["grain_code"] == "corporate")
    assert corporate["titles"] == ["Public post"]
    html = render_newspaper_html(edition)
    assert "Public post" in html
    assert "theta" not in html.lower()
    assert "θ" not in html


def test_published_html_round_trips_for_the_board_card() -> None:
    from lineageweave.newspaper_edition import edition_from_row, newspaper_thread_key

    orgmetra = SeedOrgmetraClient([OrgmetraUnit("corporate", "corp-1", "Demo Corp")])
    edition = assemble_newspaper_edition(
        kind="week",
        period_code="2026-W02",
        orgmetra=orgmetra,
        ranked_titles_by_unit={("corporate", "corp-1"): ("Public post",)},
    )
    parsed = edition_from_row(
        newspaper_thread_key("week"),
        "2026-W02",
        render_newspaper_html(edition),
    )
    assert parsed is not None
    assert parsed["period_code"] == "2026-W02"
    corporate = next(section for section in parsed["sections"] if section["grain_code"] == "corporate")
    assert corporate["titles"] == ["Public post"]
    assert "θ" not in render_newspaper_html(edition)


def test_team_grain_without_a_consumed_grouping_stays_empty() -> None:
    orgmetra = SeedOrgmetraClient([OrgmetraUnit("team", "team-1", "설계팀")])
    edition = assemble_newspaper_edition(
        kind="week",
        period_code="2026-W02",
        orgmetra=orgmetra,
        ranked_titles_by_unit={("team", "team-1"): ("Invented",)},
    )
    team = next(section for section in edition.sections if section.grain_code == "team")
    assert team.titles == ()
    assert team.empty_next_action == WEEK_EMPTY_NEXT_ACTION
