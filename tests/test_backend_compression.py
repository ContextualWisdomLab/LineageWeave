"""Response-compression contract for evidence-rich API projections."""

from starlette.middleware.gzip import GZipMiddleware

from backend.app.main import app


def test_backend_compresses_large_api_responses() -> None:
    """The API middleware must compress evidence-rich Dashboard payloads."""
    assert any(middleware.cls is GZipMiddleware for middleware in app.user_middleware)
