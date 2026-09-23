"""Guard Similar VOC pagination against stale request-scope responses."""

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


def test_similar_voc_initial_retry_invalidates_inflight_pagination_scope() -> None:
    """Retrying page 1 must make an older in-flight next page unable to append."""
    source = _APP_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r"const\s+similarVocScopeRef\s*=\s*useRef\(\{\s*postId\s*,\s*accessToken\s*,\s*similarVocRetry\s*\}\);",
        source,
    ), "Similar VOC request scope must include the initial-query retry generation"
    assert re.search(
        r"similarVocScopeRef\.current\.similarVocRetry\s*!==\s*similarVocRetry"
        r"[\s\S]{0,240}"
        r"similarVocScopeRef\.current\s*=\s*\{\s*postId\s*,\s*accessToken\s*,\s*similarVocRetry\s*\}",
        source,
    ), "Initial-query retry must rotate page-request scope before the retry effect runs"
