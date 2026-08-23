"""Correlation-ID middleware: every response carries a unique X-Request-Id,
and the fail-closed except-Exception handlers' logger stamps it onto every
log line for that request -- without touching each handler individually.

Uses TestClient without entering its lifespan context (`with TestClient(...)`),
since the middleware under test needs neither the database pool nor Redis
that `lifespan()` provisions; every other backend/tests/test_api.py test that
does need a live request/response cycle goes through the full seeded-database
fixture instead.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import _request_id_var, app


def test_response_carries_a_request_id_header() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/definitely-not-a-real-path")

    assert response.status_code == 404
    request_id = response.headers.get("x-request-id")
    assert request_id
    assert len(request_id) == 36  # canonical UUID4 string length


def test_each_request_gets_a_distinct_request_id() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    first = client.get("/definitely-not-a-real-path").headers["x-request-id"]
    second = client.get("/definitely-not-a-real-path").headers["x-request-id"]

    assert first != second


def test_client_supplied_request_id_header_is_ignored() -> None:
    """A server-generated ID only -- an inbound value is never logged verbatim,
    closing the log-injection vector an unsanitized client header would open."""
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/definitely-not-a-real-path",
        headers={"X-Request-Id": "attacker-supplied\nFAKE LOG LINE"},
    )

    assert response.headers["x-request-id"] != "attacker-supplied\nFAKE LOG LINE"
    assert len(response.headers["x-request-id"]) == 36


def test_logger_adapter_appends_the_active_request_id() -> None:
    from backend.app.main import _logger

    token = _request_id_var.set("test-request-id-123")
    try:
        message, kwargs = _logger.process("boom", {})
    finally:
        _request_id_var.reset(token)

    assert message == "boom [request_id=test-request-id-123]"
    assert kwargs == {}


def test_logger_adapter_leaves_message_unchanged_outside_a_request() -> None:
    from backend.app.main import _logger

    assert _request_id_var.get() is None
    message, kwargs = _logger.process("boom", {})

    assert message == "boom"
    assert kwargs == {}
