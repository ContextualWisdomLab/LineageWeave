"""Static checks for exact-head Dashboard runtime evidence."""

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


def test_product_images_expose_explicit_source_revision() -> None:
    """Backend and frontend images must label their operator-supplied revision."""
    for path in (_ROOT / "backend" / "Dockerfile", _ROOT / "frontend" / "Dockerfile"):
        dockerfile = path.read_text(encoding="utf-8")
        assert "ARG LINEAGEWEAVE_SOURCE_REVISION=unknown" in dockerfile
        assert (
            "LABEL org.opencontainers.image.revision=${LINEAGEWEAVE_SOURCE_REVISION}"
            in dockerfile
        )


def test_compose_passes_revision_to_all_product_images() -> None:
    """Compose must pass the same fail-closed revision input to each product build."""
    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert compose.count(
        "LINEAGEWEAVE_SOURCE_REVISION: ${LINEAGEWEAVE_SOURCE_REVISION:-unknown}"
    ) == 3


def test_synthetic_acceptance_never_enables_provider_calls() -> None:
    """The synthetic runner must stay limited to authenticated Dashboard reads."""
    runner = (_ROOT / "scripts" / "accept_operations_dashboard_synthetic.sh").read_text(
        encoding="utf-8"
    )
    assert "ALLOW_PROVIDER_CALLS" not in runner
    assert "/api/post-content" not in runner
    assert "provider_readiness" not in runner
    assert '"$BACKEND_URL/api/dashboard"' in runner


def test_provider_acceptance_reuses_shared_post_eligibility_sql() -> None:
    """The provider acceptance aggregate must not fork publication eligibility."""
    runner = (_ROOT / "scripts" / "accept_operations_dashboard_runtime.sh").read_text(
        encoding="utf-8"
    )
    assert "from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL" in runner
    assert "where ${source_post_eligibility_sql}" in runner
