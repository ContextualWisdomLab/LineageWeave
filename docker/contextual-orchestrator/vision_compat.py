"""Multimodal chat compatibility for the pinned contextual-orchestrator."""

from __future__ import annotations

from typing import Any


_ROLES = {"system", "user", "assistant"}


def _content(content: Any) -> str | list[dict[str, Any]]:
    if isinstance(content, str):
        return content
    if not isinstance(content, list) or not content:
        raise ValueError("message content must be text or non-empty content blocks")

    blocks: list[dict[str, Any]] = []
    for block in content:
        if not isinstance(block, dict):
            raise ValueError("message content blocks must be objects")
        block_type = block.get("type")
        if block_type == "text" and isinstance(block.get("text"), str):
            blocks.append({"type": "text", "text": block["text"]})
            continue
        if block_type == "image_url":
            image_url = block.get("image_url")
            url = image_url.get("url") if isinstance(image_url, dict) else None
            if not isinstance(url, str) or not (
                url.startswith("data:image/") or url.startswith("https://")
            ):
                raise ValueError("image_url must be a data image or HTTPS URL")
            normalized_url = {"url": url}
            if isinstance(image_url, dict) and isinstance(image_url.get("detail"), str):
                normalized_url["detail"] = image_url["detail"]
            blocks.append({"type": "image_url", "image_url": normalized_url})
            continue
        raise ValueError("unsupported message content block")
    return blocks


def validate_multimodal_messages(messages: Any) -> list[dict[str, Any]]:
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")

    validated: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("messages must contain objects")
        role = message.get("role")
        if role not in _ROLES:
            raise ValueError("message role is invalid")
        validated.append({"role": role, "content": _content(message.get("content"))})
    return validated


def latest_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        parts = [
            block.get("text", "")
            if block.get("type") == "text"
            else "[image]"
            for block in content
        ]
        return "\n".join(part for part in parts if part)
    return ""


def install_multimodal_chat_support() -> None:
    """Install the compatibility layer inside contextual-orchestrator."""

    from contextual_orchestrator import orchestrator, server

    if getattr(server, "_lineageweave_vision_compat", False):
        return

    def validate(messages: Any) -> list[dict[str, Any]]:
        try:
            return validate_multimodal_messages(messages)
        except ValueError as exc:
            raise server.RequestError(400, "invalid_message", str(exc)) from exc

    server._validate_messages = validate

    def latest(self: Any, messages: list[dict[str, Any]]) -> str:
        return latest_user_text(messages)

    orchestrator.TaskOrchestrator._latest_user_text = latest
    server._lineageweave_vision_compat = True
