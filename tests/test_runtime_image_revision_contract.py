"""Static checks for exact-head Dashboard runtime evidence."""

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


def test_product_images_expose_explicit_source_revision() -> None:
    """Every product image must label its operator-supplied source revision."""
    for path in (_ROOT / "backend" / "Dockerfile", _ROOT / "frontend" / "Dockerfile"):
        dockerfile = path.read_text(encoding="utf-8")
        assert "ARG LINEAGEWEAVE_SOURCE_REVISION=unknown" in dockerfile
        assert (
            "LABEL org.opencontainers.image.revision=${LINEAGEWEAVE_SOURCE_REVISION}"
            in dockerfile
        )
    frontend = (_ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert "io.contextualwisdomlab.lineageweave.oidc-issuer" in frontend
    assert "io.contextualwisdomlab.lineageweave.backend-url" in frontend

    orchestrator = (
        _ROOT / "docker" / "contextual-orchestrator" / "Dockerfile"
    ).read_text(encoding="utf-8")
    assert "ARG CONTEXTUAL_ORCHESTRATOR_SOURCE_REVISION=unknown" in orchestrator
    assert (
        "LABEL org.opencontainers.image.revision="
        "${CONTEXTUAL_ORCHESTRATOR_SOURCE_REVISION}"
    ) in orchestrator


def test_compose_passes_revision_to_all_product_images() -> None:
    """Compose must pass the same fail-closed revision input to each product build."""
    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert compose.count(
        "LINEAGEWEAVE_SOURCE_REVISION: ${LINEAGEWEAVE_SOURCE_REVISION:-unknown}"
    ) == 4
    assert (
        "CONTEXTUAL_ORCHESTRATOR_SOURCE_REVISION: "
        "2712827bfebd8be39e25c24924ad1f18522fd5f9"
    ) in compose


def test_runtime_acceptance_checks_every_product_image_revision() -> None:
    """Acceptance must reject any stale backend, worker, MCP, or frontend image."""
    runner = (_ROOT / "scripts" / "accept_operations_dashboard_runtime.sh").read_text(
        encoding="utf-8"
    )
    assert "for service_name in backend backend-worker mcp frontend; do" in runner
    assert "lineageweave-${service_name}-1" in runner
    assert '[[ ",${COMPOSE_PROFILES:-}," == *,mcp,* ]]' in runner
    assert "docker inspect lineageweave-mcp-1 >/dev/null 2>&1" in runner
    assert "start the accepted stack with COMPOSE_PROFILES=mcp" in runner


def test_synthetic_acceptance_never_enables_provider_calls() -> None:
    """The synthetic runner must stay limited to authenticated Dashboard reads."""
    runner = (_ROOT / "scripts" / "accept_operations_dashboard_synthetic.sh").read_text(
        encoding="utf-8"
    )
    assert "ALLOW_PROVIDER_CALLS" not in runner
    assert "/api/post-content" not in runner
    assert "provider_readiness" not in runner
    assert '"$BACKEND_URL/api/dashboard"' in runner
    assert 'PRODUCT_CONTAINER_PREFIX="${PRODUCT_CONTAINER_PREFIX:-lineageweave}"' in runner
    assert 'SYNTHETIC_USERNAME="${SYNTHETIC_USERNAME:-demo.admin}"' in runner
    assert "OIDC_READINESS_TIMEOUT_SECONDS" in runner


def test_provider_acceptance_reuses_shared_post_eligibility_sql() -> None:
    """The provider acceptance aggregate must not fork publication eligibility."""
    runner = (_ROOT / "scripts" / "accept_operations_dashboard_runtime.sh").read_text(
        encoding="utf-8"
    )
    assert "from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL" in runner
    assert "where ${source_post_eligibility_sql}" in runner


def test_provider_acceptance_observes_the_resumed_content_ledger() -> None:
    """Acceptance must reuse current work and prove deployment-bound evidence."""
    runner = (_ROOT / "scripts" / "accept_operations_dashboard_runtime.sh").read_text(
        encoding="utf-8"
    )
    assert "OPERATIONS_CASE_ACCEPTANCE_TIMEOUT_SECONDS" in runner
    assert "OPERATIONS_CASE_POLL_SECONDS" in runner
    assert "docker inspect lineageweave-backend-worker-1" in runner
    assert "{{.State.StartedAt}}" in runner
    assert '-v deployment_started_at="$worker_started_at"' in runner
    assert "analysis.analyzed_at >= :'deployment_started_at'::timestamptz" in runner
    assert "analysis.source_body_sha256 = job.source_body_sha256" in runner
    assert "'post_content_ingestion_queued'" in runner
    assert "'post_content_ingestion_running'" in runner
    assert "count(distinct post_id)" in runner
    assert "run_operations_case_aggregate" in runner
    assert "printf '%s\\n' \"$aggregate_sql\"" in runner
    assert 'docker exec -i "$POSTGRES_CONTAINER"' in runner
    assert '-c "$aggregate_sql"' not in runner
    assert 'sleep "$OPERATIONS_CASE_POLL_SECONDS"' in runner
    assert "/api/post-content/backfill" not in runner
    assert "expected exactly one normalized preferred candidate" not in runner
    assert "post_id=%" not in runner


def test_provider_acceptance_uses_bounded_async_gateway_readiness() -> None:
    """Runtime acceptance must probe only the declared gateway access list."""
    runner = (_ROOT / "scripts" / "accept_operations_dashboard_runtime.sh").read_text(
        encoding="utf-8"
    )
    assert "ORCHESTRATOR_PROBE_TIMEOUT_SECONDS" in runner
    assert "ORCHESTRATOR_READINESS_TIMEOUT_SECONDS" in runner
    assert "provider_readiness/latest?refresh=true" not in runner
    assert "docker exec -i" in runner
    assert "-e ORCHESTRATOR_ADMIN_TOKEN" not in runner
    assert "CONTEXTUAL_ORCHESTRATOR_TOKEN" in runner
    assert '.provider == "configured_gateway"' in runner
    assert '.status != "disabled"' in runner
    assert "/api/v1/provider_readiness_refreshes" in runner
    assert 'capability_code:"structured"' in runner
    assert 'capability_code:"chat"' not in runner
    assert 'headers["X-Request-Timeout-Ms"] = timeout_ms' in runner
    assert "remaining_readiness_ms" in runner
    assert "readiness_deadline - SECONDS" in runner
    assert '.poll_after_ms | select(type == "number" and floor == . and . > 0)' in runner
    assert 'sleep "$readiness_poll_seconds"' in runner
    assert "queued|running) sleep 1" not in runner
    assert "failed|cancelled|expired" in runner
    assert ".ready_count > 0" in runner


def test_runtime_runners_require_distinct_desktop_and_mobile_artifacts() -> None:
    """Both acceptance modes must preserve separate responsive screenshots."""
    for script_name in (
        "accept_operations_dashboard_runtime.sh",
        "accept_operations_dashboard_synthetic.sh",
    ):
        runner = (_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "SCREENSHOT_DESKTOP_PATH" in runner
        assert "SCREENSHOT_MOBILE_PATH" in runner
        assert '"$SCREENSHOT_DESKTOP_PATH" != "$SCREENSHOT_MOBILE_PATH"' in runner
        assert ".metrics.checks.fails == 0" in runner
        assert ".metrics.http_req_failed.value == 0" in runner
        assert "BACKEND_READINESS_TIMEOUT_SECONDS" in runner
        assert '"${BACKEND_URL%/}/healthz"' in runner


def test_provider_runtime_exercises_dashboard_and_ask_evidence_navigation() -> None:
    """Committed runtime acceptance preserves both evidence-bearing customer flows."""
    runner = (_ROOT / "scripts" / "accept_operations_dashboard_runtime.sh").read_text(
        encoding="utf-8"
    )
    dashboard_spec = (_ROOT / "frontend/e2e/runtime-operations-dashboard.spec.ts").read_text(
        encoding="utf-8"
    )
    ask_spec = (_ROOT / "frontend/e2e/runtime-ask-evidence.spec.ts").read_text(
        encoding="utf-8"
    )
    assert "e2e/runtime-operations-dashboard.spec.ts e2e/runtime-ask-evidence.spec.ts" in runner
    assert "evidenceDialog" in dashboard_spec
    assert "ASK_SCREENSHOT_DESKTOP_PATH" in runner
    assert "ASK_SCREENSHOT_MOBILE_PATH" in runner
    assert "ASK_SCREENSHOT_DESKTOP_PATH" in ask_spec
    assert "ASK_SCREENSHOT_MOBILE_PATH" in ask_spec
    assert "LINEAGEWEAVE_RUNTIME_ASK_QUESTION" in runner
    assert "LINEAGEWEAVE_RUNTIME_ASK_TIMEOUT_SECONDS" in runner
    assert "LINEAGEWEAVE_RUNTIME_ASK_TIMEOUT_SECONDS" in ask_spec
    assert "MINIMUM_TOKEN_LIFETIME_SECONDS" not in ask_spec
    assert "expires_at: expiresAt" in ask_spec
    assert "Date.now() / 1000) +" not in ask_spec
    assert "timeoutSeconds * 1000" in ask_spec
    assert "< timeoutSeconds" in ask_spec
    assert "620_000" not in ask_spec


def test_acceptance_uses_only_the_checked_in_compose_file() -> None:
    """Host-level Compose overrides must not alter the accepted product stack."""
    makefile = (_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "COMPOSE_FILE=docker-compose.yml docker compose" in makefile
    for script_name in (
        "accept_operations_dashboard_runtime.sh",
        "accept_operations_dashboard_synthetic.sh",
    ):
        runner = (_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "export COMPOSE_FILE=docker-compose.yml" in runner
