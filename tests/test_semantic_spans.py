from __future__ import annotations

import pytest

from lineageweave.semantic_spans import (
    CachedEmbeddingSimilarity,
    EmbeddingMetadata,
    SemanticSpanPolicy,
    TokenBudgetExceededError,
    build_micro_units,
    build_semantic_spans,
    make_semantic_span_chunker,
    normalize_unicode_text,
    render_embedding_input,
)


class _CodePointCodec:
    """Deterministic test codec: one Unicode code point equals one token."""

    def encode(self, text: str) -> list[int]:
        return [ord(character) for character in text]

    def decode(self, tokens: list[int]) -> str:
        return "".join(chr(token) for token in tokens)


class _KeywordEmbedder:
    available = True

    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        if "different" in text.lower() or "다른" in text:
            return [0.0, 1.0]
        return [1.0, 0.0]


def _policy(**overrides: object) -> SemanticSpanPolicy:
    values: dict[str, object] = {
        "model_max_tokens": 256,
        "request_reserve_tokens": 16,
        "target_span_tokens": 80,
        "max_span_tokens": 120,
        "min_span_tokens": 1,
        "max_micro_unit_tokens": 100,
        "boundary_threshold": 0.55,
        "structure_weight": 0.35,
        "semantic_weight": 0.45,
        "length_weight": 0.20,
    }
    values.update(overrides)
    return SemanticSpanPolicy(**values)


def test_normalization_preserves_script_content_and_joiners() -> None:
    text = "e\u0301\r\n한\u200b글\u200d🙂\ufeff"

    normalized = normalize_unicode_text(text)

    assert normalized == "é\n한글\u200d🙂"


def test_micro_units_split_mixed_scripts_without_language_detection_or_spaces() -> None:
    text = "한국어 문장입니다。日本語です！مرحبا بالعالم؟English sentence."

    units = build_micro_units(text, codec=_CodePointCodec(), policy=_policy())

    assert [unit.text for unit in units] == [
        "한국어 문장입니다。",
        "日本語です！",
        "مرحبا بالعالم؟",
        "English sentence.",
    ]
    assert [unit.index for unit in units] == [0, 1, 2, 3]


def test_decimal_point_is_not_treated_as_a_sentence_boundary() -> None:
    units = build_micro_units(
        "The score was 3.14. 다음 값은 2.71입니다。",
        codec=_CodePointCodec(),
        policy=_policy(),
    )

    assert units[0].text == "The score was 3.14."
    assert units[1].text == "다음 값은 2.71입니다。"


def test_dense_semantic_drop_splits_related_units_from_a_new_topic() -> None:
    codec = _CodePointCodec()
    embedder = _KeywordEmbedder()
    similarity = CachedEmbeddingSimilarity(embedder)
    text = (
        "Alpha idea continues. Alpha detail follows.\n\n"
        "A completely different topic starts here."
    )

    spans = build_semantic_spans(
        text,
        codec=codec,
        adjacent_similarity=similarity,
        policy=_policy(),
    )

    assert len(spans) == 2
    assert "Alpha detail follows." in spans[0].text
    assert spans[1].text == "A completely different topic starts here."
    # Three unique micro-units are embedded once each even though they form
    # two adjacent comparisons.
    assert len(embedder.calls) == 3


def test_related_short_paragraphs_can_merge_despite_authored_break() -> None:
    spans = build_semantic_spans(
        "First related observation.\n\nSecond related observation.",
        codec=_CodePointCodec(),
        adjacent_similarity=lambda _left, _right: 1.0,
        policy=_policy(),
    )

    assert len(spans) == 1
    assert spans[0].source_indices == (0, 1)


def test_oversized_unpunctuated_text_uses_exact_token_windows() -> None:
    codec = _CodePointCodec()
    policy = _policy(
        model_max_tokens=32,
        request_reserve_tokens=2,
        target_span_tokens=8,
        max_span_tokens=10,
        max_micro_unit_tokens=6,
    )
    text = "가나다라마바사아자차카타파하ABCDEFGHIJK"

    spans = build_semantic_spans(text, codec=codec, policy=policy)

    assert spans
    assert all(span.token_count <= 10 for span in spans)
    assert "".join(span.text.replace("\n", "") for span in spans) == text


def test_span_neighbors_are_contiguous_for_context_restoration() -> None:
    policy = _policy(
        model_max_tokens=64,
        request_reserve_tokens=4,
        target_span_tokens=6,
        max_span_tokens=8,
        max_micro_unit_tokens=6,
    )
    spans = build_semantic_spans(
        "abcdefghiABCDEFGHIabcdefghi",
        codec=_CodePointCodec(),
        policy=policy,
    )

    assert len(spans) > 2
    assert spans[0].previous_index is None
    assert spans[0].next_index == 1
    assert spans[1].previous_index == 0
    assert spans[-1].next_index is None


def test_semantic_span_chunker_plugs_into_existing_chunk_contract() -> None:
    chunker = make_semantic_span_chunker(
        codec=_CodePointCodec(),
        embedder=_KeywordEmbedder(),
        policy=_policy(),
    )

    chunks = chunker("Related note. A different subject appears.")

    assert chunks
    assert all(chunk.unit_type == "semantic_span" for chunk in chunks)
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.label.startswith("tokens:") for chunk in chunks)


def test_embedding_metadata_is_budgeted_with_the_content() -> None:
    codec = _CodePointCodec()
    policy = _policy(
        model_max_tokens=120,
        request_reserve_tokens=20,
        target_span_tokens=40,
        max_span_tokens=80,
        max_micro_unit_tokens=60,
    )
    span = build_semantic_spans("short content.", codec=codec, policy=policy)[0]

    payload = render_embedding_input(
        span,
        codec=codec,
        policy=policy,
        metadata=EmbeddingMetadata(title="T", heading_path=("A",), block_type="paragraph"),
    )

    assert "[title] T" in payload
    assert "[heading_path] A" in payload
    assert "[content]" in payload


def test_embedding_payload_overflow_is_rejected_before_provider_call() -> None:
    codec = _CodePointCodec()
    policy = _policy(
        model_max_tokens=30,
        request_reserve_tokens=5,
        target_span_tokens=15,
        max_span_tokens=20,
        max_micro_unit_tokens=20,
    )
    span = build_semantic_spans("content.", codec=codec, policy=policy)[0]

    with pytest.raises(TokenBudgetExceededError, match="budget is 25"):
        render_embedding_input(
            span,
            codec=codec,
            policy=policy,
            metadata=EmbeddingMetadata(title="X" * 30),
        )


def test_policy_rejects_a_leaf_limit_above_the_safe_provider_budget() -> None:
    with pytest.raises(ValueError, match="model input budget"):
        SemanticSpanPolicy(
            model_max_tokens=100,
            request_reserve_tokens=20,
            min_span_tokens=10,
            target_span_tokens=50,
            max_span_tokens=90,
            max_micro_unit_tokens=50,
        )


def test_similarity_must_be_finite() -> None:
    with pytest.raises(ValueError, match="finite"):
        build_semantic_spans(
            "One sentence. Another sentence.",
            codec=_CodePointCodec(),
            adjacent_similarity=lambda _left, _right: float("nan"),
            policy=_policy(),
        )


def test_tiktoken_adapter_uses_requested_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    from types import SimpleNamespace

    from lineageweave.semantic_spans import TiktokenTokenCodec

    requested: list[str] = []

    class _FakeEncoding:
        def encode(self, text: str, *, disallowed_special: tuple[()] = ()) -> list[int]:
            assert disallowed_special == ()
            return [ord(character) for character in text]

        def decode(self, tokens: list[int]) -> str:
            return "".join(chr(token) for token in tokens)

    fake_module = SimpleNamespace(
        get_encoding=lambda name: requested.append(name) or _FakeEncoding()
    )
    monkeypatch.setitem(sys.modules, "tiktoken", fake_module)

    codec = TiktokenTokenCodec("cl100k_base")

    assert requested == ["cl100k_base"]
    assert codec.encode("A한") == [ord("A"), ord("한")]
    assert codec.decode([ord("A"), ord("한")]) == "A한"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"model_max_tokens": 0}, "must be positive"),
        (
            {"model_max_tokens": 100, "request_reserve_tokens": 100},
            "smaller than model_max_tokens",
        ),
        (
            {"min_span_tokens": 90, "target_span_tokens": 80},
            "min_span_tokens <= target_span_tokens",
        ),
        (
            {"max_micro_unit_tokens": 121},
            "max_micro_unit_tokens cannot exceed",
        ),
        ({"boundary_threshold": 1.1}, "between 0 and 1"),
        ({"semantic_weight": -0.1}, "non-negative"),
        (
            {"structure_weight": 0.0, "semantic_weight": 0.0, "length_weight": 0.0},
            "sum to more than zero",
        ),
    ],
)
def test_policy_validates_all_invariants(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _policy(**overrides)


def test_structural_unit_types_are_script_neutral() -> None:
    units = build_micro_units(
        "# 제목\n- عنصر\n```\n| 日本 | 한국 |",
        codec=_CodePointCodec(),
        policy=_policy(),
    )

    assert [unit.unit_type for unit in units] == [
        "heading",
        "list_item",
        "code_fence",
        "table_row",
    ]
    assert units[1].boundary_before == 0.9


def test_repeated_terminal_marks_and_closing_quotes_remain_with_the_unit() -> None:
    units = build_micro_units(
        'Really?!" 다음입니다。』',
        codec=_CodePointCodec(),
        policy=_policy(),
    )

    assert [unit.text for unit in units] == ['Really?!"', "다음입니다。』"]


def test_empty_input_produces_no_micro_units_or_spans() -> None:
    codec = _CodePointCodec()

    assert build_micro_units("\u200b \n\n", codec=codec, policy=_policy()) == []
    assert build_semantic_spans("", codec=codec, policy=_policy()) == []


def test_empty_token_window_decode_is_ignored() -> None:
    class _DroppingCodec(_CodePointCodec):
        def decode(self, tokens: list[int]) -> str:
            if tokens and chr(tokens[0]) == "a":
                return ""
            return super().decode(tokens)

    units = build_micro_units(
        "abcdefghi",
        codec=_DroppingCodec(),
        policy=_policy(max_micro_unit_tokens=3),
    )

    assert [unit.text for unit in units] == ["def", "ghi"]
    assert units[0].index == 0


def test_embedding_similarity_rejects_dimension_mismatch() -> None:
    class _VariableDimensionEmbedder:
        def embed(self, text: str) -> list[float]:
            return [1.0] if text == "left" else [1.0, 0.0]

    similarity = CachedEmbeddingSimilarity(_VariableDimensionEmbedder())

    with pytest.raises(ValueError, match="same dimension"):
        similarity("left", "right")


def test_embedding_similarity_handles_zero_vectors() -> None:
    class _ZeroEmbedder:
        def embed(self, _text: str) -> list[float]:
            return [0.0, 0.0]

    assert CachedEmbeddingSimilarity(_ZeroEmbedder())("a", "b") == 0.0


def test_similarity_values_are_clamped_to_the_contract_range() -> None:
    policy = _policy(boundary_threshold=0.99)

    spans = build_semantic_spans(
        "One. Two.",
        codec=_CodePointCodec(),
        adjacent_similarity=lambda _left, _right: 4.0,
        policy=policy,
    )

    assert len(spans) == 1


def test_metadata_supports_speaker_date_and_content_only_payloads() -> None:
    codec = _CodePointCodec()
    policy = _policy(model_max_tokens=300, request_reserve_tokens=20)
    span = build_semantic_spans("content.", codec=codec, policy=policy)[0]

    content_only = render_embedding_input(span, codec=codec, policy=policy)
    enriched = render_embedding_input(
        span,
        codec=codec,
        policy=policy,
        metadata=EmbeddingMetadata(speaker="Speaker 1", occurred_at="2026-08-15"),
    )

    assert content_only == "content."
    assert "[speaker] Speaker 1" in enriched
    assert "[occurred_at] 2026-08-15" in enriched


def test_chunker_can_run_without_dense_provider() -> None:
    chunker = make_semantic_span_chunker(
        codec=_CodePointCodec(),
        policy=_policy(),
    )

    assert chunker("One. Two.")
