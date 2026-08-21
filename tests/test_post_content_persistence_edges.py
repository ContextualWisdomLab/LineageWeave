from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hashlib
from types import SimpleNamespace

import pytest

from lineageweave.chunking import chunk_by_dom
from lineageweave.image_content import ImageRegion
from lineageweave.post_content_normalization import (
    FormattingHint,
    ImageContentResult,
    ImageRegionResult,
    NormalizedPostContent,
)
from lineageweave.post_content_persistence import (
    _bounded_unit_batches,
    _render_image_text,
    persist_post_content,
)
from lineageweave.post_structure import StructureDecision


def _persist(*args: object, **kwargs: object) -> int:
    return asyncio.run(persist_post_content(*args, **kwargs))


class _Connection:
    def __init__(self, previous_images: tuple[dict[str, object], ...] = ()) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.fetchvals: list[tuple[str, tuple[object, ...]]] = []
        self.previous_images = previous_images
        self._next_id = 0

    @asynccontextmanager
    async def transaction(self):
        yield self

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "OK"

    async def fetchval(self, query: str, *args: object) -> str:
        self.fetchvals.append((query, args))
        self._next_id += 1
        return f"id-{self._next_id}"

    async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
        assert "post_content_image" in query
        return list(self.previous_images)


class _EmbedMany:
    available = True

    async_calls = 0

    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        self.async_calls += 1
        self.texts.extend(texts)
        return [[1.0, 2.0] for _ in texts]


class _LegacyEmbed:
    available = True

    def __init__(self, vector: list[float]) -> None:
        self.vector = vector
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return self.vector


class _UnavailableEmbed:
    available = False

    def embed(self, _text: str) -> list[float]:
        raise AssertionError("unavailable channel must not be called")


class _FailingStructure:
    """Represent an expected structure-channel response failure."""

    available = True

    def infer(
        self, _post_title: str, _units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        """Raise the response-validation error handled by persistence."""
        raise ValueError("synthetic invalid structure response")


class _UnexpectedChannelFailure:
    """Represent a programming defect that persistence must expose."""

    available = True

    def embed_many(self, _texts: list[str]) -> list[list[float]]:
        """Raise a defect outside the expected channel-failure contract."""
        raise AssertionError("synthetic programming defect")

    def infer(
        self, _post_title: str, _units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        """Raise the same defect from the structure-channel boundary."""
        raise AssertionError("synthetic programming defect")


class _ResolvedStructure:
    """Return one applicable and one out-of-scope structure decision."""

    available = True

    def infer(
        self, _post_title: str, units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        """Return bounded synthetic decisions for persistence filtering."""
        return (
            StructureDecision(
                unit_index=int(units[0]["unit_index"]),
                indent_level=2,
                confidence=0.9,
                evidence="Synthetic semantic nesting evidence.",
            ),
            StructureDecision(
                unit_index=999,
                indent_level=9,
                confidence=0.1,
                evidence="Out-of-scope synthetic decision.",
            ),
        )


def test_render_image_text_preserves_unavailable_and_caption_variants() -> None:
    assert _render_image_text(None) == "[image: content unavailable]"
    assert _render_image_text(ImageContentResult(0, "image/png", "failed")) == "[image: content unavailable]"
    assert (
        _render_image_text(
            ImageContentResult(
                0,
                "image/png",
                "described",
                SimpleNamespace(caption="caption", extracted_text="  ", tags=()),
            )
        )
        == "[image: caption]"
    )
    assert (
        _render_image_text(
            ImageContentResult(
                0,
                "image/png",
                "described",
                SimpleNamespace(caption="", extracted_text=" OCR ", tags=()),
            )
        )
        == "[image: no caption available | text: OCR]"
    )


def test_persists_image_tags_formatting_and_embeddings() -> None:
    body = '<p style="color:red">before</p><img src="data:image/png;base64,aGVsbG8="><p>after</p>'
    chunks = chunk_by_dom(body)
    image_index = next(chunk.index for chunk in chunks if chunk.unit_type == "image")
    first_dom = next(chunk for chunk in chunks if chunk.unit_type == "dom")
    normalized = NormalizedPostContent(
        text="before\n\nafter",
        formatting_hints=(FormattingHint(first_dom.index, first_dom.label, "color:red"),),
        image_results=(
            ImageContentResult(
                image_index,
                "image/png",
                "described",
                SimpleNamespace(caption="diagram", extracted_text="OCR", tags=("one", "two")),
                regions=(
                    ImageRegionResult(
                        0,
                        ImageRegion(0.0, 0.0, 1.0, 1.0),
                        "described",
                        SimpleNamespace(caption="panel", extracted_text="panel OCR", tags=("panel",)),
                    ),
                    ImageRegionResult(
                        1,
                        ImageRegion(0.1, 0.1, 0.5, 0.5),
                        "unavailable",
                        None,
                    ),
                ),
            ),
        ),
    )
    conn = _Connection(
        (
            {
                "content_sha256": hashlib.sha256(b"hello").hexdigest(),
                "extracted_text": "previous OCR",
            },
            {
                "content_sha256": hashlib.sha256(b"replaced image").hexdigest(),
                "extracted_text": "removed image OCR",
            },
        )
    )
    embedder = _EmbedMany()

    count = _persist(
        conn,
        "post-1",
        body,
        embedding_client=embedder,
        embedding_model_code="embedding-model",
        normalized_result=normalized,
    )

    assert count == len(chunks)
    assert embedder.async_calls == 1
    assert "[image: panel | text: panel OCR]" in embedder.texts
    assert any("post_content_image" in query for query, _args in conn.fetchvals)
    assert sum("post_content_image_tag" in query for query, _args in conn.executed) == 2
    assert any("post_content_image_region_embedding" in query for query, _args in conn.fetchvals)
    assert sum("post_content_image_region_embedding_value" in query for query, _args in conn.executed) == 2
    assert any("post_content_embedding" in query for query, _args in conn.fetchvals)
    assert sum("post_content_embedding_value" in query for query, _args in conn.executed) == 2 * len(chunks)


def test_same_image_retry_cannot_replace_existing_ocr_with_empty_text() -> None:
    body = '<img src="data:image/png;base64,aGVsbG8=">'
    image_index = chunk_by_dom(body)[0].index
    normalized = NormalizedPostContent(
        text="[image: updated caption]",
        image_results=(
            ImageContentResult(
                image_index,
                "image/png",
                "described",
                SimpleNamespace(caption="updated caption", extracted_text="", tags=()),
            ),
        ),
    )
    conn = _Connection(
        (
            {
                "content_sha256": hashlib.sha256(b"hello").hexdigest(),
                "description_status_code": "described",
                "extracted_text": "prior OCR",
                "caption": "prior caption",
            },
        )
    )

    with pytest.raises(RuntimeError, match="refusing to replace non-empty image OCR"):
        _persist(conn, "post-4", body, normalized_result=normalized)

    assert not any("delete from post_content_unit" in query for query, _args in conn.executed)


def test_legacy_embed_and_malformed_vectors_never_write_vectors() -> None:
    conn = _Connection()
    legacy = _LegacyEmbed([float("nan")])
    count = _persist(
        conn,
        "post-2",
        "plain text",
        embedding_client=legacy,
        embedding_model_code="embedding-model",
    )

    assert count == 1
    assert legacy.calls == ["plain text"]
    assert not any("post_content_embedding" in query for query, _args in conn.fetchvals)


def test_unavailable_embedding_channel_is_skipped_and_empty_body_is_safe() -> None:
    conn = _Connection()
    assert (
        _persist(
            conn,
            "post-3",
            "",
            embedding_client=_UnavailableEmbed(),
            embedding_model_code="embedding-model",
        )
        == 0
    )
    assert not any("post_content_embedding" in query for query, _args in conn.fetchvals)


def test_source_only_whitespace_is_not_persisted_as_explicit_depth() -> None:
    """Presentation alignment must not become authoritative hierarchy."""
    conn = _Connection()

    assert (
        _persist(
            conn,
            "post-4",
            "<p>&nbsp;&nbsp;First item</p><p>&nbsp;&nbsp;&nbsp;&nbsp;Second item</p>",
        )
        == 2
    )

    structure_rows = [
        args
        for query, args in conn.executed
        if "insert into post_content_unit_structure" in query
    ]
    assert [(args[1], args[2]) for args in structure_rows] == [
        (0, "unresolved"),
        (0, "unresolved"),
    ]


def test_expected_structure_failure_remains_unresolved_for_retry() -> None:
    """Keep an invalid provider response absent without losing source units."""
    conn = _Connection()

    assert (
        _persist(conn, "post-5", "plain text", structure_client=_FailingStructure())
        == 1
    )
    assert any(
        args[2] == "unresolved"
        for query, args in conn.executed
        if "insert into post_content_unit_structure" in query
    )


@pytest.mark.parametrize(
    "channel_kwargs",
    (
        {
            "embedding_client": _UnexpectedChannelFailure(),
            "embedding_model_code": "embedding-model",
        },
        {"structure_client": _UnexpectedChannelFailure()},
    ),
)
def test_unexpected_channel_defects_propagate(
    channel_kwargs: dict[str, object],
) -> None:
    """Expose programming defects so the durable worker records the failure."""
    with pytest.raises(AssertionError, match="synthetic programming defect"):
        _persist(_Connection(), "post-6", "plain text", **channel_kwargs)


def test_bounded_batches_cover_empty_count_and_character_limits() -> None:
    """Preserve generic keys while enforcing both provider request bounds."""
    assert _bounded_unit_batches([]) == []
    count_bounded = _bounded_unit_batches([(str(i), "x") for i in range(33)])
    assert [len(batch) for batch in count_bounded] == [32, 1]
    assert [
        len(batch)
        for batch in _bounded_unit_batches([(str(i), "x" * 12_001) for i in range(3)])
    ] == [1, 1, 1]


def test_explicit_and_adjudicated_structure_are_persisted_by_unit() -> None:
    """Persist explicit depth and only in-scope orchestrator decisions."""
    conn = _Connection()

    assert (
        _persist(
            conn,
            "post-7",
            '<p style="margin-left: 40px">Explicit</p><p>Semantic</p>',
            structure_client=_ResolvedStructure(),
        )
        == 2
    )
    structure_rows = [
        args
        for query, args in conn.executed
        if "insert into post_content_unit_structure" in query
    ]
    assert [(args[1], args[2]) for args in structure_rows] == [
        (1, "explicit"),
        (2, "llm"),
    ]
