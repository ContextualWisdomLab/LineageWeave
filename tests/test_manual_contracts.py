"""Keep customer and operator manuals aligned with shipped entry points."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MANUALS = ROOT / "docs" / "manuals"


def _text(name: str) -> str:
    """Return one checked-in manual as UTF-8 text."""
    return (MANUALS / name).read_text(encoding="utf-8")


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
            path_text = target.split("#", 1)[0]
            if not path_text or "://" in path_text:
                continue
            assert (document.parent / path_text).resolve().exists(), (
                f"{document.relative_to(ROOT)} links to missing {target}"
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


def test_user_manual_covers_every_supported_voice_code() -> None:
    """Keep the user-facing category inventory equal to the API union."""
    manual = _text("user-guide.md")
    api = (ROOT / "frontend" / "src" / "api.ts").read_text(encoding="utf-8")
    for code in ("voc", "vocc", "voco", "vom", "vop", "vos", "voe", "vob", "vor", "voi", "voso", "vops"):
        assert f'"{code}"' in api
        assert f"| {code.upper()} |" in manual


def test_operations_manual_names_current_commands_and_fail_closed_measurement() -> None:
    """Require recovery guidance for current Compose, load, and TEPP bounds."""
    manual = _text("operations-manual.md")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("up", "smoke", "load-http", "load-mcp", "down"):
        assert f"{target}:" in makefile
    assert "TEPP" in manual
    assert "unavailable" in manual
    assert "do not manufacture a score" in _text("mcp-manual.md")
