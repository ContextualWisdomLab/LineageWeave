"""Fail-closed ThreadWeave conversation port.

ThreadWeave is an in-process JWZ/RFC 5256 library. LineageWeave
threads only visible posts and visible-only lineage edges. A hidden
parent is omitted; the child becomes a root. The client never invents
a parent.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lineageweave.threadweave_client import (
    LibraryThreadWeaveTransport,
    ThreadWeaveClient,
    ThreadWeaveNotAvailable,
    build_threadweave_client,
    conversation_messages_from_rows,
    project_conversation_forest,
)


def test_default_transport_fails_closed() -> None:
    client = ThreadWeaveClient()
    with pytest.raises(ThreadWeaveNotAvailable, match="threadweave_not_available"):
        client.thread_conversations(
            [{"message_id": "post-1", "post_title": "Public post", "references": []}]
        )


def test_default_payload_never_invents_a_parent() -> None:
    payload = ThreadWeaveClient().as_api_payload(
        [{"message_id": "post-1", "post_title": "Public post", "references": []}]
    )

    assert payload == {
        "port": "threadweave",
        "status": "unavailable",
        "status_reason": "threadweave_not_available",
        "conversations": [],
    }


def test_disabled_factory_fails_closed() -> None:
    client = build_threadweave_client(disabled=True)
    payload = client.as_api_payload(
        [{"message_id": "post-1", "post_title": "Public post", "references": []}]
    )
    assert payload["status"] == "unavailable"
    assert payload["conversations"] == []


def test_library_transport_fails_closed_when_threadweave_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom() -> object:
        raise ImportError("No module named 'threadweave'")

    monkeypatch.setattr(
        "lineageweave.threadweave_client._import_threadweave", boom
    )
    client = ThreadWeaveClient(transport=LibraryThreadWeaveTransport())
    with pytest.raises(ThreadWeaveNotAvailable, match="threadweave_not_available"):
        client.thread_conversations(
            [{"message_id": "post-1", "post_title": "Public post", "references": []}]
        )
    assert client.as_api_payload(
        [{"message_id": "post-1", "post_title": "Public post", "references": []}]
    )["conversations"] == []


def test_library_transport_fails_closed_when_thread_messages_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTw:
        class Message:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

        @staticmethod
        def thread_messages(_messages: object) -> list:
            raise RuntimeError("cyclic references")

    monkeypatch.setattr(
        "lineageweave.threadweave_client._import_threadweave", lambda: FakeTw
    )
    client = ThreadWeaveClient(transport=LibraryThreadWeaveTransport())
    with pytest.raises(ThreadWeaveNotAvailable, match="threadweave_not_available"):
        client.thread_conversations(
            [{"message_id": "post-1", "post_title": "Public post", "references": []}]
        )


def test_injected_transport_returns_accepted_trees() -> None:
    def fake_transport(_messages: list[dict]) -> list[dict]:
        return [
            {
                "post_id": "post-1",
                "post_title": "Public post",
                "children": [
                    {
                        "post_id": "post-2",
                        "post_title": "Pricing renegotiation: revised quote sent",
                    }
                ],
            }
        ]

    payload = ThreadWeaveClient(transport=fake_transport).as_api_payload(
        [
            {"message_id": "post-1", "post_title": "Public post", "references": []},
            {
                "message_id": "post-2",
                "post_title": "Pricing renegotiation: revised quote sent",
                "references": ["post-1"],
            },
        ]
    )

    assert payload["status"] == "accepted"
    assert payload["status_reason"] is None
    assert payload["conversations"] == [
        {
            "post_id": "post-1",
            "post_title": "Public post",
            "children": [
                {
                    "post_id": "post-2",
                    "post_title": "Pricing renegotiation: revised quote sent",
                }
            ],
        }
    ]


def test_library_transport_projects_monkeypatched_thread_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeMessage:
        def __init__(
            self, message_id: str, references: list[str], payload: dict[str, str]
        ) -> None:
            self.message_id = message_id
            self.references = references
            self.payload = payload

    class FakeTw:
        Message = FakeMessage

        @staticmethod
        def thread_messages(messages: list[FakeMessage]) -> list:
            captured["ids"] = [message.message_id for message in messages]
            captured["refs"] = [list(message.references) for message in messages]
            root = SimpleNamespace(
                message=messages[0],
                children=[SimpleNamespace(message=messages[1], children=[])],
            )
            return [root]

    monkeypatch.setattr(
        "lineageweave.threadweave_client._import_threadweave", lambda: FakeTw
    )
    payload = ThreadWeaveClient(transport=LibraryThreadWeaveTransport()).as_api_payload(
        [
            {"message_id": "post-1", "post_title": "Public post", "references": []},
            {
                "message_id": "post-2",
                "post_title": "Pricing renegotiation: revised quote sent",
                "references": ["post-1"],
            },
        ]
    )

    assert captured["ids"] == ["post-1", "post-2"]
    assert captured["refs"] == [[], ["post-1"]]
    assert payload["conversations"][0]["post_title"] == "Public post"
    assert payload["conversations"][0]["children"][0]["post_title"] == (
        "Pricing renegotiation: revised quote sent"
    )


def test_hidden_parent_is_omitted_and_child_becomes_root() -> None:
    messages = conversation_messages_from_rows(
        posts=[
            {"post_id": "hidden-parent", "post_title": "Private parent"},
            {"post_id": "post-2", "post_title": "Pricing renegotiation: revised quote sent"},
        ],
        edges=[
            {"parent_post_id": "hidden-parent", "child_post_id": "post-2"},
        ],
        can_see_post=lambda row: str(row["post_id"]) != "hidden-parent",
    )

    assert messages == [
        {
            "message_id": "post-2",
            "post_title": "Pricing renegotiation: revised quote sent",
            "references": (),
        }
    ]

    def echo(rows: list[dict]) -> list[dict]:
        return [
            {
                "post_id": row["message_id"],
                "post_title": row["post_title"],
                "children": [],
            }
            for row in rows
        ]

    payload = ThreadWeaveClient(transport=echo).as_api_payload(messages)
    assert payload["conversations"] == [
        {
            "post_id": "post-2",
            "post_title": "Pricing renegotiation: revised quote sent",
        }
    ]
    assert all(
        "hidden-parent" not in str(tree) for tree in payload["conversations"]
    )


def test_visible_parent_is_the_only_jwz_reference() -> None:
    messages = conversation_messages_from_rows(
        posts=[
            {"post_id": "post-1", "post_title": "Public post"},
            {
                "post_id": "post-2",
                "post_title": "Pricing renegotiation: revised quote sent",
            },
        ],
        edges=[{"parent_post_id": "post-1", "child_post_id": "post-2"}],
        can_see_post=lambda _row: True,
    )
    by_id = {row["message_id"]: row for row in messages}
    assert by_id["post-1"]["references"] == ()
    assert by_id["post-2"]["references"] == ("post-1",)


def test_unknown_envelope_fails_closed() -> None:
    with pytest.raises(ThreadWeaveNotAvailable, match="threadweave_not_available"):
        project_conversation_forest({"threads": [{"post_title": "spoofed"}]})


def test_dummy_container_lifts_children_instead_of_inventing_a_parent() -> None:
    dummy = SimpleNamespace(
        message=None,
        children=[
            SimpleNamespace(
                message=SimpleNamespace(
                    message_id="post-2",
                    payload={"post_title": "Pricing renegotiation: revised quote sent"},
                ),
                children=[],
            )
        ],
    )
    forest = project_conversation_forest([dummy])
    assert [tree.to_json() for tree in forest.trees] == [
        {
            "post_id": "post-2",
            "post_title": "Pricing renegotiation: revised quote sent",
        }
    ]


def test_blank_title_is_not_repaired_into_a_parent() -> None:
    forest = project_conversation_forest(
        [
            {
                "post_id": "invented",
                "post_title": "",
                "children": [
                    {"post_id": "post-2", "post_title": "Delivery schedule question raised"}
                ],
            }
        ]
    )
    assert [tree.post_id for tree in forest.trees] == ["post-2"]
    assert all(tree.post_id != "invented" for tree in forest.trees)
