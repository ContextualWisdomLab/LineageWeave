"""Fail-closed contextual-orchestrator helper for analysis-run work.

New helpers in this slice always request ``mode="auto"``. They do not add
``mode="verify"`` calls and do not invent a portable task envelope. Missing
base URL, ``invalid_mode``, and non-2xx responses fail closed.
"""

from __future__ import annotations

from typing import Any, Callable

from .http_client import HttpClientError, post_json

Poster = Callable[..., dict[str, Any]]


class OrchestratorNotAvailable(RuntimeError):
    """Raised when the orchestrator base URL is missing or the call fails closed."""


class NullAnalysisRunOrchestrationClient:
    """No orchestrator configured -- analysis-run completion is unavailable."""

    available = False

    def complete(self, prompt: str) -> str:
        """Refuse to invent a completion when the channel is missing."""

        raise RuntimeError(
            "NullAnalysisRunOrchestrationClient cannot complete; check .available first"
        )


def request_auto_completion(
    base_url: str | None,
    prompt: str,
    *,
    api_key: str = "",
    timeout: float = 60.0,
    poster: Poster = post_json,
) -> str:
    """POST ``/v1/chat/completions`` with ``mode="auto"`` and return the text.

    Raises:
        OrchestratorNotAvailable: the base URL is missing, the orchestrator
            reports ``invalid_mode``, the HTTP status is not 2xx, or the
            response has no usable content.
    """

    if base_url is None or not str(base_url).strip():
        raise OrchestratorNotAvailable("missing orchestrator base URL")
    headers = {"authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        body = poster(
            f"{str(base_url).rstrip('/')}/v1/chat/completions",
            {
                "messages": [{"role": "user", "content": prompt}],
                "mode": "auto",
            },
            headers=headers,
            timeout=timeout,
        )
    except HttpClientError as exc:
        raise OrchestratorNotAvailable(f"orchestrator request failed: {exc}") from exc
    if body.get("error") == "invalid_mode" or body.get("code") == "invalid_mode":
        raise OrchestratorNotAvailable("invalid_mode")
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OrchestratorNotAvailable("orchestrator response missing content") from exc
    if not isinstance(content, str) or not content.strip():
        raise OrchestratorNotAvailable("orchestrator response missing content")
    return content


class ContextualOrchestratorAnalysisRunClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="auto"``."""

    available = True

    def __init__(
        self,
        base_url: str | None,
        api_key: str = "",
        *,
        timeout: float = 60.0,
        poster: Poster = post_json,
    ) -> None:
        if base_url is None or not str(base_url).strip():
            raise OrchestratorNotAvailable("missing orchestrator base URL")
        self._base_url = str(base_url).rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._poster = poster

    def complete(self, prompt: str) -> str:
        """Return one auto-mode completion for ``prompt``."""

        return request_auto_completion(
            self._base_url,
            prompt,
            api_key=self._api_key,
            timeout=self._timeout,
            poster=self._poster,
        )
