from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_grouping_comparison_axis_share_uses_visible_text_as_its_name() -> None:
    app = _read("frontend/src/App.tsx")
    app_test = _read("frontend/src/App.test.tsx")
    helper = _read("frontend/src/leftoverMapCompareAxis.ts")

    assert 'aria-label={t(LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL)}' not in app
    assert "LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL" not in app
    assert "LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL" not in helper
    assert 'getAllByLabelText(\n        "Leftover map comparison axis share"' not in app_test
    assert "leftover map comparison axis 1 0%" in app_test
    assert "LEFTOVER_MAP_COMPARE_AXIS_SHARE" in app


def test_axis_share_author_name_does_not_survive_as_dead_translation_authority() -> None:
    translations = _read("frontend/src/i18n.ts")
    translation_tests = _read("frontend/src/i18n.test.ts")

    assert '"Leftover map comparison axis share"' not in translations
    assert '"Leftover map comparison axis share"' not in translation_tests
    assert '"leftover map comparison axis {axis} {share}%"' in translations


def test_adr_and_changelog_do_not_require_a_distinct_author_name_on_plain_span() -> None:
    adr = _read("docs/adr/0367-leftover-map-compare-axis-share.md")
    changelog = _read("CHANGELOG.d/2.54.0-leftover-map-compare-axis-share.md")

    assert "Use the distinct\naccessible name `Leftover map comparison axis share`" not in adr
    assert "distinct comparison copy and accessible naming" not in changelog
    assert "leftover map comparison axis {k} {share}%" in adr
    assert "leftoverMapCompareAxisShare" in changelog
