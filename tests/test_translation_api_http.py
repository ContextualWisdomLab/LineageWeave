"""Focused HTTP contract for the authenticated translation API slice."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app import main as api
from backend.app.translation_ledger import (
    TranslationCoverageError,
    TranslationResourceNotFound,
)


def _client(*, authenticated: bool) -> TestClient:
    """Build a route-level client without starting external service lifespans."""
    api.app.dependency_overrides.clear()
    api.app.dependency_overrides[api.get_pool] = object
    api.app.dependency_overrides[api.get_valkey] = object
    if authenticated:
        api.app.dependency_overrides[api.get_current_account] = object
    return TestClient(api.app)


def _close(client: TestClient) -> None:
    """Release the client and restore global FastAPI dependency state."""
    try:
        client.close()
    finally:
        api.app.dependency_overrides.clear()


def test_translation_screen_requires_authentication(monkeypatch) -> None:
    """An unauthenticated caller must not reach the translation read model."""
    called = False

    async def fake_read(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("unauthenticated request reached translation read model")

    monkeypatch.setattr(api, "read_translation_screen", fake_read)
    client = _client(authenticated=False)
    try:
        response = client.get("/api/translations/customer-master", params={"locale": "en"})
    finally:
        _close(client)

    assert response.status_code in {401, 403}
    assert called is False


def test_translation_screen_reports_invalid_screen_identity_without_blame_on_locale() -> None:
    """A malformed screen identity must not tell a valid-locale caller to change language."""
    client = _client(authenticated=True)
    try:
        response = client.get("/api/translations/%20customer-master", params={"locale": "en"})
    finally:
        _close(client)

    assert response.status_code == 422
    assert response.json()["detail"] == "The translation screen identifier is invalid."


def test_translation_screen_reports_unrepresentable_version_without_blame_on_locale() -> None:
    """A version beyond PostgreSQL BIGINT must identify the version contract, not the locale."""
    client = _client(authenticated=True)
    try:
        response = client.get(
            "/api/translations/customer-master",
            params={"locale": "en", "resource_version": 9_223_372_036_854_775_808},
        )
    finally:
        _close(client)

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Choose a translation resource version within the supported range."
    )


def test_translation_screen_reads_authenticated_exact_version(monkeypatch) -> None:
    """The HTTP route must preserve exact screen/version/locale identity."""
    seen: dict[str, object] = {}

    async def fake_read(pool, valkey, *, product_key, screen_key, locale, resource_version):
        seen.update(
            pool=pool,
            valkey=valkey,
            product_key=product_key,
            screen_key=screen_key,
            locale=locale,
            resource_version=resource_version,
        )
        return SimpleNamespace(
            screen_key=screen_key,
            resource_version=resource_version,
            locale=locale,
            translations={"title": "Kundenstamm"},
        )

    monkeypatch.setattr(api, "read_translation_screen", fake_read)
    client = _client(authenticated=True)
    try:
        response = client.get(
            "/api/translations/customer-master",
            params={"locale": "de", "resource_version": 7},
        )
    finally:
        _close(client)

    assert response.status_code == 200
    assert response.json() == {
        "screen_key": "customer-master",
        "resource_version": 7,
        "locale": "de",
        "translations": {"title": "Kundenstamm"},
    }
    assert seen["product_key"] == "lineageweave"
    assert seen["screen_key"] == "customer-master"
    assert seen["locale"] == "de"
    assert seen["resource_version"] == 7


def test_translation_screen_maps_missing_version_without_driver_access(monkeypatch) -> None:
    """A missing published resource is a stable 404 HTTP contract."""
    async def fake_read(*args, **kwargs):
        raise TranslationResourceNotFound("missing")

    monkeypatch.setattr(api, "read_translation_screen", fake_read)
    client = _client(authenticated=True)
    try:
        response = client.get(
            "/api/translations/customer-master",
            params={"locale": "fr", "resource_version": 9},
        )
    finally:
        _close(client)

    assert response.status_code == 404
    assert response.json()["detail"] == "This screen version is not available. Refresh and try the latest version."


def test_translation_screen_maps_incomplete_locale_without_driver_access(monkeypatch) -> None:
    """An incomplete requested locale remains distinguishable from absence."""
    async def fake_read(*args, **kwargs):
        raise TranslationCoverageError("incomplete")

    monkeypatch.setattr(api, "read_translation_screen", fake_read)
    client = _client(authenticated=True)
    try:
        response = client.get("/api/translations/customer-master", params={"locale": "es"})
    finally:
        _close(client)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "This screen is not yet available in the selected language. Choose another language."
    )
