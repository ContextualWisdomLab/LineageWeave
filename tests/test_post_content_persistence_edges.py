from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from lineageweave.chunking import chunk_by_dom
from lineageweave.image_content import ImageRegion, buyer_safe_image_caption
from lineageweave.post_content_normalization import (
    FormattingHint,
    ImageContentResult,
    ImageRegionResult,
    NormalizedPostContent,
)
from lineageweave.post_content_persistence import (
    _render_image_text,
    persist_post_content,
)


def _persist(*args: object, **kwargs: object) -> int:
    return asyncio.run(persist_post_content(*args, **kwargs))


class _Connection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.fetchvals: list[tuple[str, tuple[object, ...]]] = []
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


def test_internal_image_instruction_is_not_searchable_caption() -> None:
    """Prompt guidance is not buyer evidence or embedding content."""
    assert buyer_safe_image_caption("A process diagram") == "A process diagram"
    legitimate_korean_caption = "이 이미지는 텍스트가 포함된 다이어그램을 보여줍니다"
    assert buyer_safe_image_caption(legitimate_korean_caption) == legitimate_korean_caption
    assert (
        buyer_safe_image_caption(
            "이 글의 이미지입니다. Keyman을 추출하거나 질문해 이미지 안의 텍스트를 읽으세요."
        )
        == ""
    )
    assert (
        _render_image_text(
            ImageContentResult(
                0,
                "image/png",
                "described",
                SimpleNamespace(
                    caption="This post is an image. Ask questions to read its text.",
                    extracted_text="Visible OCR",
                    tags=(),
                ),
            )
        )
        == "[image: no caption available | text: Visible OCR]"
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
                        SimpleNamespace(
                            caption="이 글의 이미지입니다. Keyman을 추출하거나 질문해 이미지 안의 텍스트를 읽으세요.",
                            extracted_text="panel OCR",
                            tags=("panel",),
                        ),
                    ),
                ),
            ),
        ),
    )
    conn = _Connection()
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
    assert "[image: no caption available | text: panel OCR]" in embedder.texts
    assert any(
        "post_content_image_region" in query and args[-1] is None
        for query, args in conn.fetchvals
    )
    assert any("post_content_image" in query for query, _args in conn.fetchvals)
    assert sum("post_content_image_tag" in query for query, _args in conn.executed) == 2
    assert any("post_content_image_region_embedding" in query for query, _args in conn.fetchvals)
    assert sum("post_content_image_region_embedding_value" in query for query, _args in conn.executed) == 2
    assert any("post_content_embedding" in query for query, _args in conn.fetchvals)
    assert sum("post_content_embedding_value" in query for query, _args in conn.executed) == 2 * len(chunks)


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
