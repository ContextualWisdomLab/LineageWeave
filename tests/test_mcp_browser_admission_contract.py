"""Repository contracts for MCP browser and request-byte admission."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    """Read one repository contract as UTF-8 text."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_environment_example_documents_the_bounded_browser_surface() -> None:
    """Operators can discover exact Origin and request-byte settings."""
    env = _read(".env.example")
    assert "MCP_ALLOWED_ORIGINS=" in env
    assert "MCP_MAX_REQUEST_BYTES=65536" in env
    assert "8192..1048576" in env
    assert "Never use `*`" in env


def test_compose_passes_the_request_limit_only_to_the_mcp_service() -> None:
    """The dedicated MCP process receives the admission limit."""
    compose = _read("docker-compose.yml")
    assert "MCP_MAX_REQUEST_BYTES: ${MCP_MAX_REQUEST_BYTES:-65536}" in compose
    before_mcp, mcp_and_after = compose.split("\n  mcp:\n", 1)
    mcp_section, after_mcp = mcp_and_after.split("\n  frontend:\n", 1)
    # The line's own right-hand-side default (${MCP_MAX_REQUEST_BYTES:-65536})
    # repeats the key text -- a bare substring count is not "one service".
    assert "MCP_MAX_REQUEST_BYTES:" not in before_mcp
    assert "MCP_MAX_REQUEST_BYTES:" not in after_mcp
    assert "MCP_ALLOWED_ORIGINS:" in mcp_section
    assert "MCP_MAX_REQUEST_BYTES:" in mcp_section


def test_integration_guide_names_every_stable_admission_error() -> None:
    """Clients receive an actionable next step for every ingress rejection."""
    guide = _read("docs/integrations/MCP.md")
    for error_code in (
        "mcp_invalid_content_length",
        "mcp_content_length_mismatch",
        "mcp_request_disconnected",
        "mcp_invalid_request_body",
        "mcp_request_too_large",
    ):
        assert error_code in guide
    assert "Vary: Origin" in guide
    assert "Mcp-Session-Id" in guide
    assert "WWW-Authenticate" in guide
    assert "browser-readable OAuth metadata" in guide
    assert "prevent process startup" in guide
    assert "Non-browser clients may omit `Origin`" in guide


def test_architecture_and_doctoring_trace_the_same_boundary() -> None:
    """The accepted decision and standards register are both present."""
    adr = _read("docs/adr/0119-mcp-browser-request-admission.md")
    references = _read("docs/doctoring/MCP_REFERENCES.md")
    changelog = _read("CHANGELOG.d/2.13.1-mcp-browser-admission.md")
    assert "Host/Origin transport validation" in adr
    assert "bounded POST body admission" in adr
    assert "WWW-Authenticate" in adr
    assert "RFC 9112" in references
    assert "WHATWG Fetch CORS protocol" in references
    assert "MCP_MAX_REQUEST_BYTES" in changelog
