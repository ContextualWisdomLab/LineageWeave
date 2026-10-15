from pathlib import Path
import os
import shutil
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "k6_http_e2e.js"
MCP_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "k6_mcp_e2e.js"


def test_k6_harness_aborts_expired_auth_and_discloses_job_state() -> None:
    """An expired owned token stops observation while job states remain visible."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert "responses.some((response) => response.status === 401)" in source
    assert "Authorized access token expired; obtain a fresh token and rerun" in source
    assert source.count("responses = readBatch(vuToken, data.askJobId)") == 1
    assert "lineageweave_ask_state_observations" in source
    assert 'job_status: String(responses[2].json("job_status_code")' in source
    assert "unitlessDuration.test(requestTimeout)" in source
    assert "REQUEST_TIMEOUT must include a duration unit" in source


@pytest.mark.parametrize("script", [SCRIPT, MCP_SCRIPT], ids=["http", "mcp"])
@pytest.mark.parametrize("token_file", ["missing", "empty"])
def test_k6_load_requires_an_owned_nonempty_token_before_network(
    script: Path, token_file: str, tmp_path: Path
) -> None:
    """Both real k6 entry points stop before requests without an owned token."""
    k6 = shutil.which("k6")
    if k6 is None:
        pytest.skip("k6 is not installed")
    environment = os.environ.copy()
    environment.pop("K6_ACCESS_TOKEN_FILE", None)
    if token_file == "empty":
        empty = tmp_path / "empty-token"
        empty.write_text("", encoding="utf-8")
        environment["K6_ACCESS_TOKEN_FILE"] = str(empty)
    result = subprocess.run(
        [k6, "run", "--quiet", "--vus", "1", "--iterations", "1", "-e", "REQUEST_TIMEOUT=2s", str(script)],
        capture_output=True,
        text=True,
        env=environment,
        timeout=15,
        check=False,
    )
    assert result.returncode != 0
    expected = "is required" if token_file == "missing" else "is empty"
    assert expected in result.stderr
    assert "http_reqs" not in result.stdout


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
