"""Guard Similar VOC pagination and rendering against stale authorization context."""

from pathlib import Path
import re


_APP_SOURCE = Path("frontend/src/App.tsx")


def test_similar_voc_pagination_scope_includes_authorization_context() -> None:
    """An in-flight page from a prior access token must not update the new session."""
    source = _APP_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r"const\s+similarVocScopeRef\s*=\s*useRef\(\{\s*postId\s*,\s*accessToken\s*\}\);",
        source,
    ), "Similar VOC request scope must bind both postId and accessToken"
    assert re.search(
        r"similarVocScopeRef\.current\.postId\s*!==\s*postId"
        r"[\s\S]{0,240}"
        r"similarVocScopeRef\.current\.accessToken\s*!==\s*accessToken"
        r"[\s\S]{0,240}"
        r"similarVocScopeRef\.current\s*=\s*\{\s*postId\s*,\s*accessToken\s*\}",
        source,
    ), "Similar VOC scope identity must rotate when either post or authorization changes"

    assert "const requestScope = similarVocScopeRef.current;" in source
    assert source.count("similarVocScopeRef.current !== requestScope") >= 2
    assert "similarVocScopeRef.current === requestScope" in source


def test_similar_voc_render_hides_evidence_from_previous_authorization_scope() -> None:
    """A token switch must not paint evidence or pagination controls from the prior account."""
    source = _APP_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r"const\s+similarVocRenderedScopeRef\s*=\s*useRef\(similarVocScopeRef\.current\);",
        source,
    ), "Similar VOC rendered evidence must remember the scope that owns the current UI state"
    assert re.search(
        r"const\s+similarVocScopeIsCurrent\s*=\s*"
        r"similarVocRenderedScopeRef\.current\s*===\s*similarVocScopeRef\.current;",
        source,
    ), "Render must compare evidence ownership with the current post+authorization scope"
    assert re.search(
        r"similarVocRenderedScopeRef\.current\s*=\s*requestScope;"
        r"[\s\S]{0,320}"
        r"setSimilarVoc\(null\)",
        source,
    ), "The fetch effect must claim the new scope before resetting and loading its evidence"
    assert "items={similarVocScopeIsCurrent ? similarVoc : null}" in source
    assert "error={similarVocScopeIsCurrent ? similarVocError : null}" in source
    assert "loadingMore={similarVocScopeIsCurrent && similarVocLoadingMore}" in source
    assert re.search(
        r"onLoadMore=\{similarVocScopeIsCurrent\s*&&\s*similarVocNextOffset\s*!==\s*null\s*\?",
        source,
    ), "A previous account's continuation must not remain interactive after authorization changes"
