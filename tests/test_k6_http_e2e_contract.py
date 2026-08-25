from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "k6_http_e2e.js"
MCP_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "k6_mcp_e2e.js"


def test_k6_harness_renews_expired_auth_and_discloses_job_state() -> None:
    """Long observations retry expired authentication and separate job states."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert "responses.some((response) => response.status === 401)" in source
    assert source.count("responses = readBatch(vuToken, data.askJobId)") == 2
    assert "lineageweave_ask_state_observations" in source
    assert 'job_status: String(responses[2].json("job_status_code")' in source
    assert "unitlessDuration.test(requestTimeout)" in source
    assert "REQUEST_TIMEOUT must include a duration unit" in source


def test_mcp_k6_harness_measures_current_authenticated_contract() -> None:
    """MCP observations initialize sessions and exercise both durable Ask tools."""
    source = MCP_SCRIPT.read_text(encoding="utf-8")

    assert '"initialize"' in source
    assert '"notifications/initialized"' in source
    assert "id === null" in source
    assert '"submit_global_ask"' in source
    assert '"read_global_ask_job"' in source
    assert "Mcp-Session-Id" in source
    assert "thresholds" not in source
    assert "REQUEST_TIMEOUT must include a duration unit" in source
