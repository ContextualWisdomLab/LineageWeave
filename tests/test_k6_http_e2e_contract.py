from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "k6_http_e2e.js"
MCP_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "k6_mcp_e2e.js"
DASHBOARD_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "k6_operations_dashboard.js"


def test_k6_harness_renews_expired_auth_and_discloses_job_state() -> None:
    """Long observations retry expired authentication and separate job states."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert "responses.some((response) => response.status === 401)" in source
    assert source.count("responses = readBatch(vuToken, data.askJobId)") == 2
    assert "lineageweave_ask_state_observations" in source
    assert 'job_status: String(responses[3].json("job_status_code")' in source
    assert '["GET", `${backendUrl}/api/dashboard`' in source
    assert 'endpoint: "dashboard"' in source
    assert 'endpoint: "post_search"' in source
    assert "encodeURIComponent(searchTerm)" in source
    assert 'lineageweave_read_duration: ["max<=20"]' in source
    assert '"lineageweave_read_duration{endpoint:post_search}": ["max<=20"]' in source
    assert 'lineageweave_ask_poll_duration: ["max<=20"]' in source


def test_k6_mcp_harness_enforces_read_latency_contract() -> None:
    """MCP read latency is a release gate rather than an observation only."""
    source = MCP_SCRIPT.read_text(encoding="utf-8")

    assert 'lineageweave_mcp_read_duration: ["max<=20"]' in source


def test_k6_dashboard_harness_enforces_read_latency_contract() -> None:
    """Dashboard latency uses the same maximum-duration release gate."""
    source = DASHBOARD_SCRIPT.read_text(encoding="utf-8")

    assert 'lineageweave_operations_dashboard_duration: ["max<=20"]' in source
    assert '"Accept-Encoding": "gzip"' in source
    assert 'value.headers["Content-Encoding"] === "gzip"' in source
