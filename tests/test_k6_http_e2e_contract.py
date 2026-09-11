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


def test_mcp_k6_harness_measures_modern_stateless_contract() -> None:
    """MCP observations default to the 2026-07-28 stateless lane with a named legacy lane."""
    source = MCP_SCRIPT.read_text(encoding="utf-8")

    assert '__ENV.MCP_PROTOCOL_VERSION || "2026-07-28"' in source
    assert '"Mcp-Method"' in source
    assert '"Mcp-Name"' in source
    assert "io.modelcontextprotocol/clientCapabilities" in source
    assert "HANDSHAKE_VERSIONS" in source
    assert '"initialize"' in source
    assert '"notifications/initialized"' in source
    assert '"submit_global_ask"' in source
    assert '"read_global_ask_job"' in source
    assert "Mcp-Session-Id" in source
    assert "thresholds" not in source
    assert "REQUEST_TIMEOUT must include a duration unit" in source


def test_mcp_k6_harness_rejects_cleartext_remote_credentials() -> None:
    """Bearer tokens and synthetic login credentials never cross remote plaintext HTTP."""
    source = MCP_SCRIPT.read_text(encoding="utf-8")
    setup_body = source[
        source.index("export function setup") : source.index("export default function")
    ]

    assert "function assertCredentialTransport" in source
    assert 'assertCredentialTransport(mcpUrl, "MCP_URL")' in setup_body
    assert 'assertCredentialTransport(keycloakUrl, "KEYCLOAK_URL")' in setup_body
    assert "LOOPBACK_HTTP" in source
    assert "^https:" in source
    assert "localhost|127\\.0\\.0\\.1|\\[::1\\]" in source
    assert "(?::\\d+)?(?:/|$)" in source


def test_mcp_k6_harness_attributes_only_matching_jsonrpc_replies() -> None:
    """A mismatched or ambiguous JSON-RPC reply is never attributed to the observation."""
    source = MCP_SCRIPT.read_text(encoding="utf-8")

    assert 'envelope.jsonrpc !== "2.0" || envelope.id !== expectedId' in source
    assert "hasResult === hasError" in source
    assert source.count("result(response, 1)") == 1
    assert source.count("structured(submitted, 3)") == 1
    assert source.count("structured(response, 4)") == 1
    assert "${response.body" not in source
    assert "JSON.stringify(envelope.error)" not in source


def test_mcp_k6_harness_observes_submit_inside_the_iteration() -> None:
    """Submit latency is sampled per iteration, not once in setup()."""
    source = MCP_SCRIPT.read_text(encoding="utf-8")
    setup_body = source[
        source.index("export function setup") : source.index("export default function")
    ]

    assert "submitDuration.add(submitted.timings.duration)" in source
    assert "submitDuration.add(response.timings.duration)" not in source
    assert '"submit_global_ask"' not in setup_body
    assert '"submit_global_ask"' in source[source.index("export default function") :]
