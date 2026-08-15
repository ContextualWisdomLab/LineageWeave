"""Language-agnostic, token-safe semantic-span construction.

This module deliberately does not identify a language, dispatch to a
language-specific tokenizer, count whitespace-delimited words, translate the
input, or use TF-IDF.  It treats the input as Unicode text and combines three
signals instead:

1. authored structure (paragraph, line, heading, list, and punctuation cues),
2. exact token accounting supplied by the embedding model's token codec, and
3. an optional dense-embedding similarity score between adjacent micro-units.

The resulting spans can be passed directly to LineageWeave's existing
``chunked_max_similarity`` function through :func:`make_semantic_span_chunker`.
The default policy is intentionally much smaller than an embedding provider's
absolute context limit; the provider limit is a safety boundary, not a target
chunk size.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, replace
from typing import Callable, Protocol, Sequence

from .chunking import Chunk


class TokenCodec(Protocol):
    """Encode and decode text exactly as the selected embedding model does."""

    def encode(self, text: str) -> list[int]: ...

    def decode(self, tokens: Sequence[int]) -> str: ...


class VectorEmbedder(Protocol):
    """Minimal adapter implemented by LineageWeave embedding clients."""

    def embed(self, text: str) -> list[float]: ...


AdjacentSimilarity = Callable[[str, str], float]


class TokenBudgetExceededError(ValueError):
    """Raised when a final embedding payload exceeds its configured budget."""


class TiktokenTokenCodec:
    """A lazy ``cl100k_base`` codec for OpenAI third-generation embeddings.

    ``tiktoken`` is imported only when this adapter is instantiated.  This
    keeps the core semantic-span algorithm provider-neutral and lets callers
    inject an authoritative codec from another service.  Deployments that use
    this adapter must install ``tiktoken`` in their embedding worker image.
    """

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        try:
            import tiktoken  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "TiktokenTokenCodec requires the optional 'tiktoken' package; "
                "install it in the embedding worker or inject another exact TokenCodec"
            ) from exc
        self._encoding = tiktoken.get_encoding(encoding_name)

    def encode(self, text: str) -> list[int]:
        """Return model tokens without allowing provider-specific specials."""
        return self._encoding.encode(text, disallowed_special=())

    def decode(self, tokens: Sequence[int]) -> str:
        """Decode a token slice back into text."""
        return self._encoding.decode(list(tokens))


@dataclass(frozen=True)
class SemanticSpanPolicy:
    """Controls token safety and boundary decisions.

    ``model_max_tokens`` is the provider's absolute input limit.
    ``request_reserve_tokens`` protects room for short metadata prefixes and
    future wire-format changes.  ``max_span_tokens`` is the much smaller
    retrieval-quality ceiling for one leaf span.
    """

    model_max_tokens: int = 8192
    request_reserve_tokens: int = 256
    target_span_tokens: int = 700
    max_span_tokens: int = 1200
    min_span_tokens: int = 120
    max_micro_unit_tokens: int = 320
    boundary_threshold: float = 0.55
    structure_weight: float = 0.35
    semantic_weight: float = 0.45
    length_weight: float = 0.20

    def __post_init__(self) -> None:
        integer_fields = {
            "model_max_tokens": self.model_max_tokens,
            "request_reserve_tokens": self.request_reserve_tokens,
            "target_span_tokens": self.target_span_tokens,
            "max_span_tokens": self.max_span_tokens,
            "min_span_tokens": self.min_span_tokens,
            "max_micro_unit_tokens": self.max_micro_unit_tokens,
        }
        for name, value in integer_fields.items():
            if value < 0 or (name != "request_reserve_tokens" and value == 0):
                raise ValueError(f"{name} must be positive (reserve may be zero)")
        if self.request_reserve_tokens >= self.model_max_tokens:
            raise ValueError("request_reserve_tokens must be smaller than model_max_tokens")
        if not self.min_span_tokens <= self.target_span_tokens <= self.max_span_tokens:
            raise ValueError("expected min_span_tokens <= target_span_tokens <= max_span_tokens")
        if self.max_micro_unit_tokens > self.max_span_tokens:
            raise ValueError("max_micro_unit_tokens cannot exceed max_span_tokens")
        if self.max_span_tokens > self.usable_input_tokens:
            raise ValueError("max_span_tokens cannot exceed the model input budget after reserve")
        if not 0.0 <= self.boundary_threshold <= 1.0:
            raise ValueError("boundary_threshold must be between 0 and 1")
        weights = (self.structure_weight, self.semantic_weight, self.length_weight)
        if any(weight < 0.0 for weight in weights) or sum(weights) <= 0.0:
            raise ValueError("boundary weights must be non-negative and sum to more than zero")

    @property
    def usable_input_tokens(self) -> int:
        """Maximum final request size after the metadata safety reserve."""
        return self.model_max_tokens - self.request_reserve_tokens


@dataclass(frozen=True)
class MicroUnit:
    """One small, ordered unit from which semantic spans are packed."""

    text: str
    index: int
    token_count: int
    boundary_before: float
    unit_type: str


@dataclass(frozen=True)
class SemanticSpan:
    """A token-safe leaf span plus lineage-friendly adjacency metadata."""

    text: str
    index: int
    token_count: int
    source_indices: tuple[int, ...]
    source_unit_types: tuple[str, ...]
    boundary_score: float
    previous_index: int | None = None
    next_index: int | None = None


@dataclass(frozen=True)
class EmbeddingMetadata:
    """Short, high-signal context that may prefix a leaf span."""

    title: str = ""
    heading_path: tuple[str, ...] = ()
    block_type: str = ""
    speaker: str = ""
    occurred_at: str = ""


# Terminal punctuation is intentionally script-diverse and does not depend on
# knowing which language produced the input.  A decimal point between digits
# is treated as data rather than a sentence boundary.
_TERMINATORS = frozenset(".!?。！？｡؟۔։።᙮꘎꛳…")
_CLOSERS = frozenset("\"'”’»›）)]}】〕〗〙〛」』〉》")
_ZERO_WIDTH_TRANSLATION = str.maketrans({"\u200b": None, "\ufeff": None})
_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")
_MARKDOWN_HEADING = re.compile(r"^#{1,6}(?:\s|$)")
_LIST_ITEM = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")


def normalize_unicode_text(text: str) -> str:
    """Normalize transport noise while preserving language and content.

    NFC normalization composes canonically equivalent sequences.  CRLF/CR
    become LF, and only the zero-width space and BOM are removed; ZWJ/ZWNJ are
    preserved because they may be meaningful in scripts and emoji sequences.
    """

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = unicodedata.normalize("NFC", normalized)
    return normalized.translate(_ZERO_WIDTH_TRANSLATION).strip()


def _token_count(codec: TokenCodec, text: str) -> int:
    return len(codec.encode(text))


def _line_unit_type(line: str) -> str:
    if _MARKDOWN_HEADING.match(line):
        return "heading"
    if _LIST_ITEM.match(line):
        return "list_item"
    if line.startswith("```") or line.startswith("~~~"):
        return "code_fence"
    if "|" in line and line.count("|") >= 2:
        return "table_row"
    return "text"


def _split_at_universal_terminators(line: str) -> list[str]:
    """Split a line without language, script, or capitalization assumptions."""

    pieces: list[str] = []
    start = 0
    cursor = 0
    while cursor < len(line):
        char = line[cursor]
        if char not in _TERMINATORS:
            cursor += 1
            continue
        if (
            char == "."
            and cursor > 0
            and cursor + 1 < len(line)
            and line[cursor - 1].isdigit()
            and line[cursor + 1].isdigit()
        ):
            cursor += 1
            continue
        end = cursor + 1
        while end < len(line) and line[end] in _TERMINATORS:
            end += 1
        while end < len(line) and line[end] in _CLOSERS:
            end += 1
        piece = line[start:end].strip()
        if piece:
            pieces.append(piece)
        start = end
        cursor = end
    remainder = line[start:].strip()
    if remainder:
        pieces.append(remainder)
    return pieces


def _token_window_units(
    text: str,
    *,
    codec: TokenCodec,
    window_size: int,
    inherited_boundary: float,
    inherited_type: str,
) -> list[tuple[str, float, str]]:
    """Last-resort exact-token split for a structurally indivisible unit."""

    tokens = codec.encode(text)
    units: list[tuple[str, float, str]] = []
    for offset in range(0, len(tokens), window_size):
        decoded = codec.decode(tokens[offset : offset + window_size]).strip()
        if not decoded:
            continue
        units.append(
            (
                decoded,
                inherited_boundary if not units else 0.15,
                inherited_type if not units else "token_window",
            )
        )
    return units


def build_micro_units(
    text: str,
    *,
    codec: TokenCodec,
    policy: SemanticSpanPolicy = SemanticSpanPolicy(),
) -> list[MicroUnit]:
    """Create Unicode, structure, and token-aware units without language ID."""

    normalized = normalize_unicode_text(text)
    if not normalized:
        return []

    pending: list[tuple[str, float, str]] = []
    paragraphs = [paragraph for paragraph in _PARAGRAPH_BREAK.split(normalized) if paragraph.strip()]
    for paragraph_index, paragraph in enumerate(paragraphs):
        lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
        for line_index, line in enumerate(lines):
            unit_type = _line_unit_type(line)
            if paragraph_index == 0 and line_index == 0:
                structural_boundary = 1.0
            elif line_index == 0:
                structural_boundary = 0.75
            else:
                structural_boundary = 0.45
            if unit_type in {"heading", "list_item", "code_fence", "table_row"}:
                structural_boundary = max(structural_boundary, 0.90)

            pieces = _split_at_universal_terminators(line) or [line]
            for piece_index, piece in enumerate(pieces):
                boundary = structural_boundary if piece_index == 0 else 0.25
                piece_type = unit_type if len(pieces) == 1 else f"{unit_type}_sentence"
                if _token_count(codec, piece) <= policy.max_micro_unit_tokens:
                    pending.append((piece, boundary, piece_type))
                else:
                    pending.extend(
                        _token_window_units(
                            piece,
                            codec=codec,
                            window_size=policy.max_micro_unit_tokens,
                            inherited_boundary=boundary,
                            inherited_type=piece_type,
                        )
                    )

    return [
        MicroUnit(
            text=unit_text,
            index=index,
            token_count=_token_count(codec, unit_text),
            boundary_before=boundary,
            unit_type=unit_type,
        )
        for index, (unit_text, boundary, unit_type) in enumerate(pending)
        if unit_text
    ]


def _join_micro_units(units: Sequence[MicroUnit]) -> str:
    """Retain visible structure without reintroducing language assumptions."""

    return "\n\n".join(unit.text for unit in units)


def _clamp_similarity(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("adjacent similarity must be finite")
    return min(1.0, max(0.0, value))


def _score_boundary(
    current_units: Sequence[MicroUnit],
    current_tokens: int,
    next_unit: MicroUnit,
    *,
    adjacent_similarity: AdjacentSimilarity | None,
    policy: SemanticSpanPolicy,
) -> float:
    structure = next_unit.boundary_before
    if adjacent_similarity is None:
        semantic_drop = 0.0
    else:
        similarity = _clamp_similarity(
            adjacent_similarity(current_units[-1].text, next_unit.text)
        )
        semantic_drop = 1.0 - similarity
    length_pressure = min(1.0, current_tokens / policy.target_span_tokens)
    numerator = (
        policy.structure_weight * structure
        + policy.semantic_weight * semantic_drop
        + policy.length_weight * length_pressure
    )
    denominator = policy.structure_weight + policy.semantic_weight + policy.length_weight
    return numerator / denominator


def _materialize_span(
    units: Sequence[MicroUnit],
    *,
    codec: TokenCodec,
    index: int,
    boundary_score: float,
) -> SemanticSpan:
    text = _join_micro_units(units)
    return SemanticSpan(
        text=text,
        index=index,
        token_count=_token_count(codec, text),
        source_indices=tuple(unit.index for unit in units),
        source_unit_types=tuple(unit.unit_type for unit in units),
        boundary_score=boundary_score,
    )


def build_semantic_spans(
    text: str,
    *,
    codec: TokenCodec,
    adjacent_similarity: AdjacentSimilarity | None = None,
    policy: SemanticSpanPolicy = SemanticSpanPolicy(),
) -> list[SemanticSpan]:
    """Pack micro-units into coherent spans while proving token safety.

    The algorithm is greedy and deterministic for a fixed codec, similarity
    function, and policy.  Dense similarity is optional so ingestion can fail
    open to structure-plus-budget chunking when an embedding provider is
    unavailable; it never falls back to TF-IDF or language-specific logic.
    """

    units = build_micro_units(text, codec=codec, policy=policy)
    if not units:
        return []

    spans: list[SemanticSpan] = []
    current: list[MicroUnit] = []
    current_start_score = 1.0

    def flush() -> None:
        nonlocal current
        if not current:  # pragma: no cover - internal invariant guard
            return
        span = _materialize_span(
            current,
            codec=codec,
            index=len(spans),
            boundary_score=current_start_score,
        )
        if span.token_count > policy.max_span_tokens:  # pragma: no cover - codec invariant
            raise AssertionError("semantic span exceeded max_span_tokens")
        if span.token_count > policy.usable_input_tokens:  # pragma: no cover - policy invariant
            raise AssertionError("semantic span exceeded provider input budget")
        spans.append(span)
        current = []

    for unit in units:
        if not current:
            current = [unit]
            current_start_score = 1.0 if not spans else unit.boundary_before
            continue

        current_text = _join_micro_units(current)
        current_tokens = _token_count(codec, current_text)
        candidate_tokens = _token_count(codec, _join_micro_units([*current, unit]))
        boundary_score = _score_boundary(
            current,
            current_tokens,
            unit,
            adjacent_similarity=adjacent_similarity,
            policy=policy,
        )
        exceeds_maximum = candidate_tokens > policy.max_span_tokens
        crosses_semantic_boundary = (
            current_tokens >= policy.min_span_tokens
            and boundary_score >= policy.boundary_threshold
        )

        if exceeds_maximum or crosses_semantic_boundary:
            flush()
            current_start_score = 1.0 if exceeds_maximum else boundary_score
            current = [unit]
        else:
            current.append(unit)

    flush()

    last_index = len(spans) - 1
    return [
        replace(
            span,
            previous_index=span.index - 1 if span.index > 0 else None,
            next_index=span.index + 1 if span.index < last_index else None,
        )
        for span in spans
    ]


class CachedEmbeddingSimilarity:
    """Convert an existing embedding client into an adjacent-similarity scorer."""

    def __init__(self, embedder: VectorEmbedder) -> None:
        self._embedder = embedder
        self._cache: dict[str, list[float]] = {}

    def _vector(self, text: str) -> list[float]:
        if text not in self._cache:
            self._cache[text] = self._embedder.embed(text)
        return self._cache[text]

    def __call__(self, left: str, right: str) -> float:
        left_vector = self._vector(left)
        right_vector = self._vector(right)
        if len(left_vector) != len(right_vector):
            raise ValueError("embedding vectors must have the same dimension")
        left_norm = math.sqrt(sum(value * value for value in left_vector))
        right_norm = math.sqrt(sum(value * value for value in right_vector))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        cosine = sum(a * b for a, b in zip(left_vector, right_vector)) / (
            left_norm * right_norm
        )
        return min(1.0, max(0.0, (cosine + 1.0) / 2.0))


def make_semantic_span_chunker(
    *,
    codec: TokenCodec,
    embedder: VectorEmbedder | None = None,
    policy: SemanticSpanPolicy = SemanticSpanPolicy(),
) -> Callable[[str], list[Chunk]]:
    """Return a ``chunked_max_similarity``-compatible semantic chunker."""

    similarity = CachedEmbeddingSimilarity(embedder) if embedder is not None else None

    def chunker(text: str) -> list[Chunk]:
        spans = build_semantic_spans(
            text,
            codec=codec,
            adjacent_similarity=similarity,
            policy=policy,
        )
        return [
            Chunk(
                text=span.text,
                unit_type="semantic_span",
                index=span.index,
                label=f"tokens:{span.token_count}",
            )
            for span in spans
        ]

    return chunker


def render_embedding_input(
    span: SemanticSpan,
    *,
    codec: TokenCodec,
    policy: SemanticSpanPolicy = SemanticSpanPolicy(),
    metadata: EmbeddingMetadata = EmbeddingMetadata(),
) -> str:
    """Render high-signal metadata plus content and enforce the final limit."""

    prefix: list[str] = []
    if metadata.title:
        prefix.append(f"[title] {metadata.title}")
    if metadata.heading_path:
        prefix.append(f"[heading_path] {' > '.join(metadata.heading_path)}")
    if metadata.block_type:
        prefix.append(f"[block_type] {metadata.block_type}")
    if metadata.speaker:
        prefix.append(f"[speaker] {metadata.speaker}")
    if metadata.occurred_at:
        prefix.append(f"[occurred_at] {metadata.occurred_at}")
    payload = "\n".join([*prefix, "[content]", span.text]) if prefix else span.text
    token_count = _token_count(codec, payload)
    if token_count > policy.usable_input_tokens:
        raise TokenBudgetExceededError(
            f"embedding payload has {token_count} tokens; budget is {policy.usable_input_tokens}"
        )
    return payload
