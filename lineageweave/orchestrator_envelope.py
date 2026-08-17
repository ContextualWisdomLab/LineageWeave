"""Fail-closed parser for contextual-orchestrator chat envelopes.

Issue #79 / ADR 0014: a versioned error envelope is not a confidence
score. Missing choices, a machine ``error_code``, or a non-object body
raise :class:`OrchestratorEnvelopeError`. Callers must drop the channel,
never treat the failure as 0.0.
"""

from __future__ import annotations

from typing import Any


class OrchestratorEnvelopeError(RuntimeError):
    """The orchestrator returned an unusable envelope."""

    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        super().__init__(message)


def parse_chat_completion(body: object) -> str:
    """Return the first choice's text, or fail closed.

    Accepts the OpenAI-shaped success object used by
    ``POST /v1/chat/completions``. An ``error_code`` field (TEPP-style
    portable envelope) is always an error, even if ``choices`` is also
    present. Unknown extra fields are ignored on success so a later
    orchestrator revision cannot force a rewrite.
    """
    if not isinstance(body, dict):
        raise OrchestratorEnvelopeError("invalid_envelope", "orchestrator body must be a JSON object")
    if "error_code" in body:
        code = str(body.get("error_code") or "orchestrator_error")
        message = str(body.get("message") or code)
        raise OrchestratorEnvelopeError(code, message)
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OrchestratorEnvelopeError("missing_choices", "orchestrator response has no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise OrchestratorEnvelopeError("invalid_choice", "orchestrator choice must be an object")
    message_obj: Any = first.get("message")
    if not isinstance(message_obj, dict):
        raise OrchestratorEnvelopeError("missing_content", "orchestrator choice has no message")
    content = message_obj.get("content")
    if not isinstance(content, str) or not content.strip():
        raise OrchestratorEnvelopeError("missing_content", "orchestrator message has no text")
    return content
