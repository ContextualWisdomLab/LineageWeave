"""Explicit, post-scoped metadata context for contextual-orchestrator calls."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Iterator, Mapping
import uuid


_POST_SESSION_NAMESPACE = uuid.UUID("6e4b3d4b-15b1-4a8a-9e38-4dd2d8c4e55c")
_CURRENT_METADATA: ContextVar[dict[str, str] | None] = ContextVar(
    "lineageweave_llm_metadata", default=None
)
_POST_METADATA_FIELDS = {
    "visibility": "visibility_code",
    "pu": "source_process_unit_code",
    "author_id": "author_account_id",
    "corp_code": "corporate_entity_code",
    "source_author_code": "source_author_code",
    "source_company_code": "source_company_code",
    "source_customer_code": "source_customer_code",
    "source_project_code": "source_project_code",
    "source_sales_pool_code": "source_sales_pool_code",
}


def build_post_llm_metadata(post_id: str, values: Mapping[str, object]) -> dict[str, str]:
    """Build non-body provenance metadata for every request about one post."""
    post_id_text = str(post_id)
    metadata = {
        "lineageweave_post_session_id": str(
            uuid.uuid5(_POST_SESSION_NAMESPACE, post_id_text)
        ),
        "lineageweave_post_id": post_id_text,
    }
    for metadata_name, source_name in _POST_METADATA_FIELDS.items():
        value = values.get(source_name)
        if value is not None and str(value).strip():
            metadata[f"lineageweave_{metadata_name}"] = str(value).strip()
    return metadata


def current_llm_metadata() -> dict[str, str] | None:
    """Return a copy of the active request metadata, if any."""
    value = _CURRENT_METADATA.get()
    return dict(value) if value else None


@contextmanager
def use_llm_metadata(metadata: Mapping[str, object]) -> Iterator[None]:
    """Make post provenance explicit for the duration of LLM transport calls."""
    parent = _CURRENT_METADATA.get() or {}
    merged = dict(parent)
    merged.update({str(key): str(value) for key, value in metadata.items() if value is not None})
    token = _CURRENT_METADATA.set(merged)
    try:
        yield
    finally:
        _CURRENT_METADATA.reset(token)
