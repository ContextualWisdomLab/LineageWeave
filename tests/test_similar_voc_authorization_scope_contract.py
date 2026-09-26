"""Guard the parent pagination scope against stale authorization context.

React rendering and scope reset are exercised by SimilarVocPanel.test.tsx.
"""

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


def test_similar_voc_scope_ref_rotates_only_after_commit() -> None:
    """An abandoned concurrent render must not mutate the live pagination scope ref."""
    source = _APP_SOURCE.read_text(encoding="utf-8")

    assert "useLayoutEffect" in source, "Commit-phase scope rotation must use React useLayoutEffect"
    assert re.search(
        r"useLayoutEffect\(\(\)\s*=>\s*\{[\s\S]{0,360}"
        r"similarVocScopeRef\.current\.postId\s*!==\s*postId[\s\S]{0,220}"
        r"similarVocScopeRef\.current\.accessToken\s*!==\s*accessToken[\s\S]{0,220}"
        r"similarVocScopeRef\.current\s*=\s*\{\s*postId\s*,\s*accessToken\s*\}[\s\S]{0,180}"
        r"\},\s*\[postId,\s*accessToken\]\);",
        source,
    ), "Similar VOC request scope must rotate in commit phase, never as a render side effect"
