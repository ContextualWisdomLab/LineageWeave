"""Contracts for fail-closed contextual-orchestrator promotion."""

from pathlib import Path

import pytest

from scripts import verify_orchestrator_provider_readiness as readiness


_ROOT = Path(__file__).resolve().parents[1]


def test_promotion_probes_current_compose_env_before_recreate() -> None:
    """The canonical service cannot be replaced before configured-gateway proof."""
    script = (_ROOT / "scripts" / "promote_contextual_orchestrator.sh").read_text()
    verify_at = script.index("verify_orchestrator_provider_readiness.py")
    recreate_at = script.index("docker compose up -d --no-deps orchestrator")
    assert verify_at < recreate_at
    assert "docker compose run -d --no-deps" in script
    assert 'json.load(sys.stdin)["services"]["orchestrator"]["image"]' in script
    assert "docker compose images -q" not in script
    assert "--env-file" not in script
    assert "docker run" not in script
    assert "LLM_GATEWAY_API_KEY" not in script
    assert "LLM_GATEWAY_API_URL" not in script
    assert "-e CONTEXTUAL_ORCHESTRATOR_ADMIN_TOKEN" in script
    assert "docker rm -f \"$preflight_container\"" in script


def test_readiness_uses_orchestrator_admin_refresh_boundary() -> None:
    """Preflight must use the orchestrator's authenticated refresh contract."""
    verifier = (_ROOT / "scripts" / "verify_orchestrator_provider_readiness.py").read_text()
    assert "/api/v1/provider_readiness/latest?refresh=true" in verifier
    assert "/api/v1/provider_readiness_refreshes" not in verifier
    assert '"provider") == "configured_gateway"' in verifier
    assert 'item.get("status") == "ready"' in verifier
    assert "CONTEXTUAL_ORCHESTRATOR_ADMIN_TOKEN" in verifier
    assert "LLM_GATEWAY_API_KEY" not in verifier
    assert "LLM_GATEWAY_API_URL" not in verifier


def test_auth_failed_configured_gateway_blocks_promotion(monkeypatch: pytest.MonkeyPatch) -> None:
    """A completed probe without a ready configured endpoint fails closed."""
    responses = iter(
        [
            {"items": [{"provider": "configured_gateway", "status": "failed", "agent_id": "synthetic-agent"}]},
            {"job_id": "synthetic-job", "status": "completed", "ready_count": 0},
        ]
    )
    monkeypatch.setattr(readiness, "_request", lambda *_args, **_kwargs: next(responses))
    with pytest.raises(RuntimeError, match="did not authenticate"):
        readiness.verify("synthetic-container", 1.0, 5)


def test_ready_configured_gateway_allows_promotion(monkeypatch: pytest.MonkeyPatch) -> None:
    """One authoritative ready result satisfies preflight."""
    monkeypatch.setattr(
        readiness,
        "_request",
        lambda *_args, **_kwargs: {
            "items": [
                {
                    "provider": "configured_gateway",
                    "status": "ready",
                    "agent_id": "synthetic-agent",
                }
            ]
        },
    )
    readiness.verify("synthetic-container", 1.0, 5)
