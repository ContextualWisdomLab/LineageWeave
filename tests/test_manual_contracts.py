"""Keep customer and operator manuals aligned with shipped entry points."""

import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
MANUALS = ROOT / "docs" / "manuals"


def _text(name: str) -> str:
    """Return one checked-in manual as UTF-8 text."""
    return (MANUALS / name).read_text(encoding="utf-8")


def _markdown_anchors(content: str) -> set[str]:
    """Return GitHub-style anchors for the headings in one Markdown file."""
    anchors: set[str] = set()
    occurrences: dict[str, int] = {}
    headings: list[str] = []
    fence_marker: tuple[str, int] | None = None
    for line in content.splitlines():
        if fence_marker is not None:
            marker_character, marker_length = fence_marker
            closing_fence = re.match(
                rf"^ {{0,3}}{re.escape(marker_character)}{{{marker_length},}}[ \t]*$",
                line,
            )
            if closing_fence is not None:
                fence_marker = None
            continue
        opening_fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if opening_fence is not None:
            marker = opening_fence.group(1)
            fence_marker = (marker[0], len(marker))
            continue
        heading = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*#*$", line)
        if heading is not None:
            headings.append(heading.group(1))
    for heading in headings:
        base = re.sub(r"[^\w\- ]", "", heading.lower())
        base = re.sub(r"\s+", "-", base.strip())
        occurrence = occurrences.get(base, 0)
        occurrences[base] = occurrence + 1
        anchors.add(base if occurrence == 0 else f"{base}-{occurrence}")
    return anchors


def test_markdown_anchor_parser_ignores_fenced_code_comments() -> None:
    """Do not accept a shell comment as proof that a linked heading exists."""
    content = "# Real heading\n```bash\n# Not a heading\n```\n~~~sh\n## Also not\n~~~~\n"
    assert _markdown_anchors(content) == {"real-heading"}


def test_manual_cross_links_resolve() -> None:
    """Require the three manuals and their relative cross-links to exist."""
    for name in ("user-guide.md", "mcp-manual.md", "operations-manual.md"):
        assert (MANUALS / name).is_file()
    assert "[operations manual](operations-manual.md)" in _text("user-guide.md")
    assert "[MCP manual](mcp-manual.md)" in _text("operations-manual.md")
    assert "[user guide](user-guide.md)" in _text("operations-manual.md")


def test_local_manual_links_resolve() -> None:
    """Reject broken fragment-free links from README or the manual set."""
    documents = [ROOT / "README.md", *sorted(MANUALS.glob("*.md"))]
    for document in documents:
        content = document.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", content):
            path_text, _, fragment = target.partition("#")
            if not path_text or "://" in path_text:
                continue
            linked_document = (document.parent / path_text).resolve()
            assert linked_document.exists(), (
                f"{document.relative_to(ROOT)} links to missing {target}"
            )
            if fragment:
                linked_content = linked_document.read_text(encoding="utf-8")
                assert unquote(fragment) in _markdown_anchors(linked_content), (
                    f"{document.relative_to(ROOT)} links to missing anchor {target}"
                )


def test_mcp_manual_names_only_current_tools_and_async_contract() -> None:
    """Bind the MCP guide to the two registered tools and durable job id."""
    manual = _text("mcp-manual.md")
    server = (ROOT / "backend" / "app" / "mcp_server.py").read_text(encoding="utf-8")
    for tool_name in ("submit_global_ask", "read_global_ask_job"):
        assert f"def {tool_name}(" in server
        assert f"`{tool_name}`" in manual
    assert "ask_job_id" in manual
    assert "cited_source_references" in manual
    assert "Mcp-Session-Id" in manual
    assert "no authorized citations" in manual
    assert "do not turn the empty evidence set into an answer" in manual


def test_user_manual_covers_every_supported_voice_code() -> None:
    """Keep the user-facing category inventory equal to the API union."""
    manual = _text("user-guide.md")
    api = (ROOT / "frontend" / "src" / "api.ts").read_text(encoding="utf-8")
    api_union = re.search(r"voice_concept_code:\s*([^;]+);", api)
    assert api_union is not None
    api_codes = set(re.findall(r'"([a-z]+)"', api_union.group(1)))
    manual_codes = set(re.findall(r"^\| ([A-Z]+) \|", manual, flags=re.MULTILINE))
    assert {code.upper() for code in api_codes} == manual_codes


def test_user_manual_gives_evidence_bound_semantic_next_actions() -> None:
    """Buyer guidance must distinguish missing evidence from negative facts."""
    manual = _text("user-guide.md")
    assert "source carries the exact\nproject code" in manual
    assert "A completed answer with no authorized citations" in manual
    assert "Source categories and supported\nderived categories remain separate" in manual
    assert "request product reprocessing" in manual


def test_operations_manual_names_current_commands_and_fail_closed_measurement() -> None:
    """Require recovery guidance for current Compose, load, and TEPP bounds."""
    manual = _text("operations-manual.md")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("up", "smoke", "load-http", "load-mcp", "down"):
        assert f"{target}:" in makefile
    assert "TEPP" in manual
    assert "unavailable" in manual
    assert "scripts/requeue_failed_post_content.py" in manual
    assert (ROOT / "scripts" / "requeue_failed_post_content.py").is_file()
    assert "do not manufacture a score" in _text("mcp-manual.md")


def test_operations_manual_covers_semantic_recovery_and_safe_promotion() -> None:
    """Operator actions must preserve receipts, exact binding, and preflight."""
    manual = _text("operations-manual.md")
    assert "scripts/promote_contextual_orchestrator.sh" in manual
    assert "EXPECTED_ORCHESTRATOR_REVISION" in manual
    assert "HTTP 401" in manual
    assert "current `~/.env`" in manual
    assert "existing canonical service remains untouched" in manual
    assert "twelve governed Voice codes are multi-label" in manual
    assert "non-empty analysis receipt" in manual
    assert "Product extraction runs independently" in manual
    assert "exact non-empty `source_project_code`" in manual
