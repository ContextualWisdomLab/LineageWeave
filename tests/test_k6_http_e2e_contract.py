from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "k6_http_e2e.js"
MCP_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "k6_mcp_e2e.js"


def _assert_machine_auth(source: str) -> None:
    """Load harnesses must use the confidential automation actor, never ROPC."""
    assert 'grant_type: "client_credentials"' in source
    assert "client_secret: clientSecret" in source
    assert "KEYCLOAK_CLIENT_SECRET" in source
    assert 'grant_type: "password"' not in source
    assert 'clientId = __ENV.KEYCLOAK_CLIENT_ID || "lineageweave-test-automation"' in source


def test_k6_harness_renews_expired_auth_and_discloses_job_state() -> None:
    """Long observations retry expired authentication and separate job states."""
    source = SCRIPT.read_text(encoding="utf-8")

    _assert_machine_auth(source)
    assert "responses.some((response) => response.status === 401)" in source
    assert source.count("responses = readBatch(vuToken, data.askJobId)") == 2
    assert "lineageweave_ask_state_observations" in source
    assert 'job_status: String(responses[2].json("job_status_code")' in source
    assert "unitlessDuration.test(requestTimeout)" in source
    assert "REQUEST_TIMEOUT must include a duration unit" in source


def test_mcp_k6_harness_measures_current_authenticated_contract() -> None:
    """MCP observations initialize sessions and exercise both durable Ask tools."""
    source = MCP_SCRIPT.read_text(encoding="utf-8")

    _assert_machine_auth(source)
    assert '"initialize"' in source
    assert '"notifications/initialized"' in source
    assert "id === null" in source
    assert '"submit_global_ask"' in source
    assert '"read_global_ask_job"' in source
    assert "Mcp-Session-Id" in source
    assert "thresholds" not in source
    assert "REQUEST_TIMEOUT must include a duration unit" in source
