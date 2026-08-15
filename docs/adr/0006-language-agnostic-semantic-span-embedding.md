# ADR 0006 — Language-agnostic semantic spans for token-safe embeddings

**Decision status:** Accepted  
**Date:** 2026-08-15

## Context

LineageWeave already embeds paragraph-level units so a short relevant passage is
not diluted by a complete document. The existing sentence helper, however,
contains script and capitalization assumptions, and neither the paragraph nor
sentence path proves that a final request fits the selected embedding model's
input context. Fixed token windows would solve overflow but cut authored meaning
and depend on duplicate overlap to restore context. Language-routed NLP stacks
would fail on code-switching and would make language classification an
unnecessary operational dependency.

The product requirement is stricter: segmentation must work without caring
which language produced the text, must remain below the
`text-embedding-3-large` context limit, and must not use TF-IDF.

OpenAI currently documents an 8,192-token input maximum for
`text-embedding-3-large`, recommends Tiktoken with `cl100k_base` for
third-generation embedding token counts, and normalizes embedding vectors so
cosine similarity is an appropriate ranking measure. Unicode NFC provides a
stable canonical representation without erasing compatibility distinctions.

## Decision

Add `lineageweave.semantic_spans` and make it the planned successor to the
legacy paragraph/sentence-only embedding segmentation path.

The module:

- never identifies a language or dispatches by language/script;
- normalizes input to NFC, standardizes line endings, and preserves ZWJ/ZWNJ;
- creates micro-units from authored structure and script-diverse terminal
  punctuation;
- accepts an exact model `TokenCodec`, with a lazy `cl100k_base` Tiktoken
  adapter supplied for `text-embedding-3-large` deployments;
- uses exact token windows only as the last-resort split for one structurally
  indivisible unit;
- combines structural boundary strength, dense adjacent semantic drop, and
  current-length pressure;
- defaults to a 700-token target, 1,200-token leaf ceiling, and 256-token final
  request reserve beneath the provider maximum;
- caches each unique micro-unit embedding during adjacency comparisons;
- continues with structure plus token budget when the dense provider is absent,
  rather than fabricating similarity or falling back to TF-IDF;
- renders only high-signal metadata and re-counts the final payload before the
  provider call; and
- exposes previous/next indices and a `Chunk` adapter so the existing
  `chunked_max_similarity` API can consume the new spans.

The accepted boundary score is:

```text
B_i = (
    0.35 * structure_break
  + 0.45 * (1 - adjacent_dense_similarity)
  + 0.20 * min(1, current_tokens / target_tokens)
)
```

A semantic boundary is taken only after the current span reaches its minimum
size and `B_i >= 0.55`; an impending token-ceiling violation always takes a
boundary. All weights, thresholds, and token targets are policy-versioned and
must be tuned on retrieval evidence before default-on production rollout.

Generative LLM work—section/document summaries, synthetic evaluation queries,
and ambiguous-case adjudication—must go through contextual-orchestrator. It is
not part of the deterministic leaf-packing hot path.

The detailed product, persistence, evaluation, rollout, and governance plan is
in [`../language-agnostic-semantic-span-plan.md`](../language-agnostic-semantic-span-plan.md).

## Consequences

### Positive

- One path handles arbitrary and mixed Unicode scripts.
- Exact model token accounting makes provider overflow preventable and
  testable.
- Dense semantic changes can create boundaries without TF-IDF or morphology.
- Existing embedding clients and `chunked_max_similarity` remain compatible.
- Policy and codec injection allow model changes without rewriting the packer.
- Neighbor metadata prepares hierarchical context restoration without making
  fixed overlap the primary design.

### Costs and limitations

- Dense adjacency scoring adds embedding work during indexing; production must
  batch and cache calls.
- Punctuation remains an imperfect weak boundary cue, especially for
  abbreviations; dense similarity and span packing mitigate rather than erase
  that ambiguity.
- The hosted OpenAI API does not expose token-level hidden states required for
  true late chunking, so this implementation performs pre-embedding semantic
  segmentation.
- The baseline PR does not yet add persistence migrations, parent summaries, or
  a default-on feature flag. Those are explicit rollout phases, not implied to
  exist.
- `TiktokenTokenCodec` imports Tiktoken lazily; a deployment choosing that
  adapter must include Tiktoken in the embedding worker or inject another exact
  codec.

## Alternatives rejected

### Language-specific morphology and sentence tokenizers

Rejected as a required control path. They introduce language identification,
code-switching failure modes, and per-language maintenance. They may be optional
research signals later but cannot determine the safety budget.

### TF-IDF/TextTiling lexical cohesion

Rejected for this feature. TextTiling motivates topic-boundary thinking, but
TF-IDF/lexical cohesion is not the requested semantic signal. Dense adjacency
similarity supplies the semantic component.

### Fixed token windows with global overlap

Rejected as the primary design because they split meaning mechanically and
multiply storage. Exact windows remain only the final safety fallback;
parent/neighbor links restore context.

### Translate everything into one language

Rejected because it increases cost and latency, can alter names and domain
meaning, and makes source-grounded offsets difficult to audit.

### Whole-document embedding

Rejected because it can exceed the provider limit and dilute short relevant
passages.

## Verification

This change includes synthetic tests covering:

- Korean, Japanese, Arabic, and English in one no-language-label input;
- punctuation without whitespace or capitalization assumptions;
- decimal preservation;
- structural unit types;
- dense semantic boundaries and embedding-cache reuse;
- provider-free deterministic fallback;
- oversized punctuation-free token windows;
- contiguous neighbor links;
- final metadata-plus-content overflow rejection;
- invalid policy configurations; and
- the existing `Chunk` adapter contract.

The new module is covered at 100% in the focused test run and makes no network
calls.

## References (APA 7th)

Günther, M., Mohr, I., Williams, D. J., Wang, B., & Xiao, H. (2024). *Late chunking: Contextual chunk embeddings using long-context embedding models* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2409.04701

Hearst, M. A. (1997). TextTiling: Segmenting text into multi-paragraph subtopic passages. *Computational Linguistics, 23*(1), 33–64. https://aclanthology.org/J97-1003/

OpenAI. (2026). *Embeddings guide*. OpenAI API documentation. Retrieved August 15, 2026, from https://platform.openai.com/docs/guides/embeddings

OpenAI. (2026). *Embeddings FAQ*. OpenAI Help Center. Retrieved August 15, 2026, from https://help.openai.com/en/articles/6824809-embeddings-faq

The Unicode Consortium. (2025). *Unicode Standard Annex #15: Unicode normalization forms* (Revision 57). https://www.unicode.org/reports/tr15/

The Unicode Consortium. (2025). *Unicode Standard Annex #29: Unicode text segmentation* (Revision 47). https://www.unicode.org/reports/tr29/
