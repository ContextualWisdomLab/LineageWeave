"""Fail-closed naruon mailbox port.

Naruon is the mailbox control plane. LineageWeave consumes only the
published inbox envelope (GET /api/emails) and never invents a thread
or a message body.
"""

from __future__ import annotations

import pytest

from lineageweave.http_client import HttpClientError
from lineageweave.naruon_client import (
    HttpNaruonTransport,
    NaruonClient,
    NaruonNotAvailable,
    parse_inbox,
)


def test_default_transport_fails_closed() -> None:
    client = NaruonClient()
    with pytest.raises(NaruonNotAvailable, match="naruon_not_available"):
        client.list_inbox()


def test_default_payload_never_invents_a_thread() -> None:
    payload = NaruonClient().as_api_payload()

    assert payload == {
        "port": "naruon",
        "status": "unavailable",
        "status_reason": "naruon_not_available",
        "threads": [],
    }


def test_parse_inbox_projects_published_fields_only() -> None:
    inbox = parse_inbox(
        {
            "emails": [
                {
                    "subject": "Quarterly plan",
                    "thread_id": "thread-root@example.com",
                    "reply_count": 3,
                    "body": "must not be copied",
                }
            ]
        }
    )

    assert len(inbox.threads) == 1
    thread = inbox.threads[0]
    assert thread.subject == "Quarterly plan"
    assert thread.thread_id == "thread-root@example.com"
    assert thread.reply_count == 3
    assert not hasattr(thread, "body")


def test_parse_inbox_rejects_unknown_envelope() -> None:
    with pytest.raises(NaruonNotAvailable, match="naruon_not_available"):
        parse_inbox({"messages": [{"subject": "spoofed"}]})


def test_parse_inbox_skips_malformed_rows_without_inventing() -> None:
    inbox = parse_inbox(
        {
            "emails": [
                {"subject": "", "thread_id": "blank-subject"},
                {"subject": "No thread id"},
                {"subject": "Quarterly plan", "thread_id": "thread-root@example.com"},
            ]
        }
    )

    assert [thread.subject for thread in inbox.threads] == ["Quarterly plan"]


def test_injected_transport_returns_accepted_threads() -> None:
    def fake_transport() -> dict:
        return {
            "emails": [
                {
                    "subject": "Quarterly plan",
                    "thread_id": "thread-root@example.com",
                    "reply_count": 2,
                }
            ]
        }

    payload = NaruonClient(transport=fake_transport).as_api_payload()

    assert payload["status"] == "accepted"
    assert payload["status_reason"] is None
    assert payload["threads"] == [
        {
            "thread_id": "thread-root@example.com",
            "subject": "Quarterly plan",
            "reply_count": 2,
        }
    ]


def test_http_transport_posts_published_inbox_path(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_get_json(url: str, *, headers: dict[str, str] | None = None, timeout: float) -> dict:
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {
            "emails": [
                {"subject": "Quarterly plan", "thread_id": "thread-root@example.com", "reply_count": 1}
            ]
        }

    monkeypatch.setattr("lineageweave.naruon_client.get_json", fake_get_json)
    transport = HttpNaruonTransport(base_url="https://naruon.example", bearer="demo-bearer")
    inbox = NaruonClient(transport=transport).list_inbox()

    assert captured["url"] == "https://naruon.example/api/emails"
    assert captured["headers"] == {"Authorization": "Bearer demo-bearer"}
    assert inbox.threads[0].subject == "Quarterly plan"


@pytest.mark.parametrize(
    "error",
    [
        HttpClientError("HTTP 503 from naruon.example"),
        HttpClientError("HTTP 404 from naruon.example"),
        TimeoutError("timed out"),
        OSError("network down"),
        ValueError("refusing non-http(s) URL scheme: 'file'"),
    ],
)
def test_http_transport_fail_closed_on_transport_errors(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def boom(*_args: object, **_kwargs: object) -> dict:
        raise error

    monkeypatch.setattr("lineageweave.naruon_client.get_json", boom)
    client = NaruonClient(transport=HttpNaruonTransport(base_url="https://naruon.example"))
    with pytest.raises(NaruonNotAvailable, match="naruon_not_available"):
        client.list_inbox()
    assert client.as_api_payload()["threads"] == []
