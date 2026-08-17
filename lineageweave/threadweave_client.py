"""Fail-closed adapter for ThreadWeave's in-process JWZ/RFC 5256 threader.

`ThreadWeave <https://github.com/ContextualWisdomLab/ThreadWeave>`_ is a
library, not an HTTP service (see its ``docs/API_CONTRACT.md``). This
client is the only LineageWeave port that may call ``thread_messages``
for the buyer-facing Conversations surface. Reconstruction already uses
ThreadWeave inside ``reconstruct.py``; this module does not replace
that path and does not invent a parent.

The default transport raises :class:`ThreadWeaveNotAvailable` so a
disabled or missing library is fail-closed, the same discipline as
:class:`lineageweave.tepp_client.TeppNotAvailable`. Wiring the
in-process library is additive (``LibraryThreadWeaveTransport``), not
a redesign.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


class ThreadWeaveNotAvailable(RuntimeError):
    """Raised when the ThreadWeave conversation port is down or disabled."""

    reason = "threadweave_not_available"


def conversation_messages_from_rows(
    posts: list[Mapping[str, Any]],
    edges: list[Mapping[str, Any]],
    can_see_post: Callable[[Mapping[str, Any]], bool],
) -> list[dict[str, Any]]:
    """Project ABAC-visible posts into ThreadWeave message dicts.

    Only edges whose parent *and* child are visible become JWZ
    ``references``. A child whose parent is hidden has an empty
    reference list and threads as a root. Never invent a parent.
    """
    visible = [row for row in posts if can_see_post(row)]
    visible_ids = {str(row["post_id"]) for row in visible}
    parents_of: dict[str, list[str]] = {}
    for edge in edges:
        parent_id = str(edge["parent_post_id"])
        child_id = str(edge["child_post_id"])
        if parent_id in visible_ids and child_id in visible_ids:
            parents_of.setdefault(child_id, []).append(parent_id)
    messages: list[dict[str, Any]] = []
    for row in visible:
        title = str(row.get("post_title") or "").strip()
        if not title:
            continue
        post_id = str(row["post_id"])
        messages.append(
            {
                "message_id": post_id,
                "post_title": title,
                "references": tuple(parents_of.get(post_id, ())),
            }
        )
    return messages


def _no_transport(_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raise ThreadWeaveNotAvailable(
        "threadweave_not_available: ThreadWeave conversation port is not "
        "configured. Pass THREADWEAVE_DISABLED=0 (default) or a transport= "
        "callable. Never invent a parent."
    )


def _import_threadweave() -> Any:
    """Import ThreadWeave at call time so a missing package fail-closes."""
    import threadweave as tw

    return tw


@dataclass(frozen=True)
class ConversationNode:
    """One visible post in a ThreadWeave tree. Never a fabricated parent."""

    post_id: str
    post_title: str
    children: tuple["ConversationNode", ...] = ()

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "post_id": self.post_id,
            "post_title": self.post_title,
        }
        if self.children:
            payload["children"] = [child.to_json() for child in self.children]
        return payload


@dataclass(frozen=True)
class ConversationForest:
    """Accepted conversation projection. Empty when ThreadWeave returned no trees."""

    trees: tuple[ConversationNode, ...]

    def to_json(self) -> list[dict[str, Any]]:
        return [tree.to_json() for tree in self.trees]


def _title_from_payload(payload: object) -> str:
    if isinstance(payload, dict):
        return str(payload.get("post_title") or "").strip()
    return ""


def _nodes_from_container(container: object) -> list[ConversationNode]:
    """Project a ThreadWeave container. Dummy or untitled nodes lift children.

    JWZ creates dummy containers for referenced-but-missing ids. A hidden
    parent must never become a buyer-visible node: omit it and let the
    visible child become a root.
    """
    child_nodes: list[ConversationNode] = []
    for child in getattr(container, "children", ()) or ():
        child_nodes.extend(_nodes_from_container(child))
    message = getattr(container, "message", None)
    if message is None:
        return child_nodes
    post_id = str(getattr(message, "message_id", "") or "").strip()
    title = _title_from_payload(getattr(message, "payload", None))
    if not post_id or not title:
        return child_nodes
    return [
        ConversationNode(
            post_id=post_id,
            post_title=title,
            children=tuple(child_nodes),
        )
    ]


def _nodes_from_mapping(item: MappingLike) -> list[ConversationNode]:
    raw_children = item.get("children") or []
    child_nodes: list[ConversationNode] = []
    if isinstance(raw_children, list):
        for child in raw_children:
            child_nodes.extend(_project_tree(child))
    post_id = str(item.get("post_id") or item.get("message_id") or "").strip()
    title = str(item.get("post_title") or "").strip()
    if not post_id or not title:
        return child_nodes
    return [
        ConversationNode(
            post_id=post_id,
            post_title=title,
            children=tuple(child_nodes),
        )
    ]


# Typed as a protocol-shaped mapping without importing Protocol just for this.
MappingLike = dict[str, Any]


def _project_tree(item: object) -> list[ConversationNode]:
    if item is None:
        return []
    if isinstance(item, dict):
        return _nodes_from_mapping(item)
    if hasattr(item, "message") or hasattr(item, "children"):
        return _nodes_from_container(item)
    return []


def project_conversation_forest(raw: object) -> ConversationForest:
    """Accept transport output. Unknown shapes fail closed. Never invent a parent."""
    if not isinstance(raw, list):
        raise ThreadWeaveNotAvailable(
            "threadweave_not_available: conversation envelope is not a tree list"
        )
    trees: list[ConversationNode] = []
    for item in raw:
        trees.extend(_project_tree(item))
    return ConversationForest(trees=tuple(trees))


class LibraryThreadWeaveTransport:
    """Call ThreadWeave ``thread_messages`` in-process. Import is inside the call."""

    def __call__(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        try:
            tw = _import_threadweave()
        except ImportError as exc:
            raise ThreadWeaveNotAvailable(
                "threadweave_not_available: threadweave package is not installed. "
                "Never invent a parent."
            ) from exc
        tw_messages = []
        for row in messages:
            message_id = str(row.get("message_id") or "").strip()
            title = str(row.get("post_title") or "").strip()
            if not message_id or not title:
                continue
            references = [
                str(ref).strip()
                for ref in (row.get("references") or ())
                if str(ref).strip()
            ]
            tw_messages.append(
                tw.Message(
                    message_id=message_id,
                    references=references,
                    payload={"post_title": title},
                )
            )
        try:
            roots = tw.thread_messages(tw_messages)
        except Exception as exc:
            raise ThreadWeaveNotAvailable(
                f"threadweave_not_available: thread_messages failed ({exc})"
            ) from exc
        forest = ConversationForest(
            trees=tuple(
                node
                for root in roots
                for node in _nodes_from_container(root)
            )
        )
        return forest.to_json()


def build_threadweave_client(disabled: bool = False) -> "ThreadWeaveClient":
    """``disabled=True`` keeps the default fail-closed transport."""
    if disabled:
        return ThreadWeaveClient()
    return ThreadWeaveClient(transport=LibraryThreadWeaveTransport())


class ThreadWeaveClient:
    """Threads visible posts through a pluggable ThreadWeave transport."""

    def __init__(
        self,
        transport: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] = _no_transport,
    ) -> None:
        self._transport = transport

    def thread_conversations(self, messages: list[dict[str, Any]]) -> ConversationForest:
        try:
            raw = self._transport(messages)
        except ThreadWeaveNotAvailable:
            raise
        except Exception as exc:
            raise ThreadWeaveNotAvailable(
                f"threadweave_not_available: conversation transport failed ({exc})"
            ) from exc
        return project_conversation_forest(raw)

    def as_api_payload(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Buyer-visible conversation status. Never invents a parent."""
        try:
            forest = self.thread_conversations(messages)
        except ThreadWeaveNotAvailable:
            return {
                "port": "threadweave",
                "status": "unavailable",
                "status_reason": ThreadWeaveNotAvailable.reason,
                "conversations": [],
            }
        return {
            "port": "threadweave",
            "status": "accepted",
            "status_reason": None,
            "conversations": forest.to_json(),
        }
