# Language-Agnostic Semantic Span Embedding Plan

**Product:** LineageWeave  
**Decision owner:** ContextualWisdomLab  
**Date:** 2026-08-15  
**Status:** Implementation baseline proposed in this change

## 1. Executive decision

LineageWeave will stop treating language identification as a prerequisite for
embedding segmentation. The ingestion path will accept arbitrary Unicode text,
including documents that mix scripts inside the same paragraph, and will build
embedding inputs from:

1. authored document structure;
2. exact token counts from the selected embedding model's codec; and
3. optional dense-embedding similarity between adjacent micro-units.

The system will not use TF-IDF, whitespace-delimited word counts,
translation-first preprocessing, or language-specific morphology as a control
path. A language label may be stored for analytics, but it must not select a
chunking algorithm or change the token budget.

The first implementation is `lineageweave.semantic_spans`. It is directly
compatible with the existing `chunked_max_similarity` contract through
`make_semantic_span_chunker`.

## 2. Why LineageWeave owns this capability

LineageWeave already has all of the adjacent responsibilities:

- an OpenAI-compatible embedding client;
- paragraph, sentence, DOM, image, and conversation-turn chunking;
- chunk-level maximum similarity for lineage reconstruction;
- contextual-orchestrator as the approved path for paid model calls; and
- tests for embedding and chunk behavior.

The capability therefore belongs beside the existing embedding channel rather
than in TEPP, which owns temporal-relational measurement, or in
contextual-orchestrator, which owns provider routing and policy rather than
document semantics. The algorithm remains provider-neutral so other
ContextualWisdomLab products can import it later instead of reimplementing it.

## 3. Problem statement

A document-wide embedding can over-compress several topics into one vector and
can exceed the provider's input context. A fixed token window prevents overflow
but cuts through authored meaning, duplicates content through overlap, and loses
section context. Language-routed tokenizers add another failure mode:
code-switching, translated quotations, product names, source code, and mixed
CJK/Latin/Arabic content can occur in the same span.

For `text-embedding-3-large`, OpenAI currently documents a maximum input of
8,192 tokens and recommends `cl100k_base`/Tiktoken for token accounting. The
absolute limit is a guardrail, not a desirable retrieval unit. This plan keeps a
256-token final-payload reserve and defaults leaf spans to a 700-token target
with a 1,200-token ceiling.

## 4. Product outcomes

The product must provide:

- **zero provider overflow:** no submitted embedding payload may exceed its
  configured model budget;
- **language-independent behavior:** identical code paths for every Unicode
  script and for mixed-script content;
- **meaning-preserving retrieval units:** short related units may merge, while
  a dense semantic drop can create a boundary before the token ceiling;
- **traceable context restoration:** every leaf span has stable order and
  previous/next links, with parent levels added during hierarchical indexing;
- **reproducibility:** policy version, model, tokenizer/codec, dimensions,
  source offsets, and content hash can be persisted; and
- **graceful degradation:** provider unavailability removes the dense signal
  and continues with structure plus exact token budget; it never invents a
  similarity score or falls back to TF-IDF.

## 5. Non-goals

This work does not:

- infer a language and select an NLP pipeline;
- translate all content into English before embedding;
- define tokens by characters, bytes, words, or whitespace;
- use TF-IDF/BM25 as a semantic-boundary surrogate;
- claim that punctuation alone is a perfect sentence segmenter;
- expose a raw model API key from LineageWeave; or
- implement late chunking inside a hosted model whose token-level hidden states
  are not exposed.

BM25 may still exist independently as a retrieval channel elsewhere, but it is
not a segmentation dependency and is not a fallback for this feature.

## 6. User stories

### US-1: mixed-script analyst search

As an analyst, I can search records containing any mixture of scripts and
receive the passage that carries the relevant meaning rather than a diluted
whole-document vector.

**Acceptance:** the runtime receives no language label, still returns token-safe
semantic spans, and preserves source order.

### US-2: ingestion operator safety

As an ingestion operator, I can change the embedding model's tokenizer and
context limit through an explicit policy/codec without editing the segmentation
algorithm.

**Acceptance:** an invalid policy fails at startup; final metadata-plus-content
payloads are checked before the provider call.

### US-3: lineage investigator context

As a lineage investigator, I can expand a matching span to its previous, next,
and parent context without re-embedding the complete document.

**Acceptance:** leaf spans expose contiguous neighbor indices; persistence adds
parent and sibling relationships without duplicating source text.

### US-4: auditor reproducibility

As an auditor, I can identify which policy, tokenizer, model, vector dimension,
and source content produced a stored vector.

**Acceptance:** persisted records are immutable by version and identified by
content hashes.

## 7. Functional requirements

| ID | Requirement |
| --- | --- |
| FR-01 | Normalize input as Unicode NFC and standardize line endings without compatibility folding. |
| FR-02 | Preserve ZWJ/ZWNJ; remove only transport-noise zero-width space/BOM. |
| FR-03 | Generate micro-units from paragraph, line, heading, list, table, code-fence, and script-diverse terminal-punctuation signals. |
| FR-04 | Do not call language identification or language-specific morphological analyzers. |
| FR-05 | Count tokens with an injected codec authoritative for the selected embedding model. |
| FR-06 | Recursively reduce an oversized unit, ending with exact token-window splitting as the last resort. |
| FR-07 | Score adjacent boundaries with structure, dense semantic drop, and length pressure. |
| FR-08 | Split unconditionally before adding a unit that would exceed `max_span_tokens`. |
| FR-09 | Validate the final metadata-plus-content payload against `model_max_tokens - request_reserve_tokens`. |
| FR-10 | Return source-unit membership and previous/next span indices. |
| FR-11 | Adapt spans to the existing `Chunk` interface. |
| FR-12 | Cache each micro-unit embedding during adjacent comparisons. |
| FR-13 | Continue deterministically without a dense provider using structure and token budget only. |

## 8. Non-functional requirements

- New algorithm unit coverage: **100%**.
- Provider overflow rate: **0%**.
- Deterministic result for a fixed normalized input, codec, embedding vectors,
  and policy.
- No network access in unit tests.
- No real customer or employer data in fixtures.
- Linear span packing after micro-unit embeddings are available.
- Bounded memory proportional to one document's micro-units and vectors.
- All future database object names use two-or-more-word `snake_case` names and
  remain in third normal form.

## 9. Processing architecture

```text
Unicode input
  -> NFC/transport normalization
  -> authored-structure parser
  -> language-agnostic micro-units
  -> exact model-token accounting
  -> optional cached dense adjacency similarity
  -> semantic boundary score
  -> token-safe leaf span packing
  -> metadata payload guard
  -> embedding provider via contextual-orchestrator
  -> leaf/section/document vector indexes
  -> candidate retrieval + parent/neighbor expansion
```

### 9.1 Micro-units

A micro-unit is not the final retrieval chunk. It is a small ordered piece from
which spans are packed. Boundary strengths are structural priors, not language
rules:

- first unit: `1.00`;
- Markdown heading/list/table/code boundary: at least `0.90`;
- new authored paragraph: `0.75`;
- new non-empty line: `0.45`; and
- subsequent terminal-punctuation unit on the same line: `0.25`.

A period between two digits is preserved as a decimal rather than split.
Terminal punctuation covers several Unicode scripts and does not require a
following space or an uppercase next character.

### 9.2 Boundary equation

For candidate boundary `i`:

```text
B_i = (
    w_structure * S_i
  + w_semantic  * (1 - similarity(E_(i-1), E_i))
  + w_length    * min(1, current_tokens / target_tokens)
) / sum(weights)
```

Default weights:

```text
w_structure = 0.35
w_semantic  = 0.45
w_length    = 0.20
threshold   = 0.55
```

The packer starts a new span when either:

1. adding the unit would exceed the leaf ceiling; or
2. the current span has reached the minimum size and `B_i >= threshold`.

These defaults are hypotheses and must be tuned against a labeled retrieval
set. They are versioned configuration, not universal constants.

### 9.3 Token policy

```text
model_max_tokens      = 8192
request_reserve       = 256
usable_request_budget = 7936
minimum_leaf          = 120
leaf_target           = 700
leaf_ceiling          = 1200
micro_unit_ceiling    = 320
```

The leaf ceiling is deliberately far below the provider maximum. Metadata is
rendered only from short, high-signal fields such as title, heading path,
block type, speaker, and event date. The final renderer counts those fields and
the content together; it rejects overflow before any HTTP request.

### 9.4 Dense boundary provider

`CachedEmbeddingSimilarity` accepts the existing LineageWeave embedding-client
shape (`embed(text) -> vector`). Production calls continue through
contextual-orchestrator's OpenAI-compatible endpoint. The cache ensures one
vector per unique micro-unit within a document.

The next optimization is a batched embedding call for all micro-units in a
document. It changes transport efficiency, not segmentation semantics.

### 9.5 LLM responsibilities

A generative LLM is not in the deterministic leaf-packing hot path. Through
contextual-orchestrator it may later:

- produce section/document summaries;
- generate synthetic evaluation queries;
- adjudicate ambiguous offline boundary examples; and
- explain why a retrieved leaf belongs to a lineage candidate.

It must not silently rewrite source content, invent a missing signal, or make a
raw provider call from this repository.

## 10. Hierarchical retrieval design

### Level 0: leaf spans

- primary precision index;
- original source text;
- stable source offsets and content hash;
- previous/next links;
- default 120–1,200 tokens.

### Level 1: section spans

- parent of contiguous leaf spans under an authored heading or inferred section;
- concise extractive or LLM-assisted summary;
- used for candidate narrowing and context restoration.

### Level 2: document spans

- one document-level descriptor and summary;
- used for coarse routing, filters, and document-level ranking.

Recommended retrieval flow:

1. embed the query once;
2. retrieve document/section candidates;
3. search leaf vectors inside those candidates;
4. rerank;
5. expand selected leaves with parent and bounded neighbor context; and
6. deduplicate parallel or overlapping evidence before generation.

Fixed overlap is reserved for the final token-window fallback. Hierarchical and
neighbor links are the default context-restoration mechanism.

## 11. Proposed normalized persistence model

No migration is included in this baseline PR. The implementation phase should
introduce these third-normal-form objects:

### `embedding_policy_version`

- `embedding_policy_id` (PK)
- `policy_version_code` (unique)
- `model_name_text`
- `token_codec_name`
- `model_token_limit`
- `request_reserve_count`
- `target_span_count`
- `maximum_span_count`
- `minimum_span_count`
- `vector_dimension_count`
- `policy_payload_json`
- `created_at`

### `embedding_document_record`

- `embedding_document_id` (PK)
- `tenant_account_id` (FK where tenancy applies)
- `source_record_id` (FK to the owning source record)
- `source_content_hash`
- `document_title_text`
- `created_at`

### `semantic_span_record`

- `semantic_span_id` (PK)
- `embedding_document_id` (FK)
- `parent_span_id` (nullable self-FK)
- `embedding_policy_id` (FK)
- `span_level_code`
- `span_order_number`
- `source_start_offset`
- `source_end_offset`
- `content_token_count`
- `content_hash_value`
- `content_text`
- `created_at`

Unique constraint:
`(embedding_document_id, span_level_code, span_order_number)`.

### `semantic_span_edge`

- `semantic_span_edge_id` (PK)
- `source_span_id` (FK)
- `target_span_id` (FK)
- `edge_type_code` (`edge_previous`, `edge_next`, `edge_parent`,
  `edge_parallel`)
- `created_at`

### `embedding_vector_record`

- `embedding_vector_id` (PK)
- `semantic_span_id` (FK)
- `embedding_policy_id` (FK)
- `vector_dimension_count`
- `vector_value`
- `created_at`

This separates source identity, span structure, versioned policy, and generated
vectors. A new vector model does not overwrite source spans or historical
vectors.

## 12. API and code usage

```python
from lineageweave.embedding_client import (
    OpenAiCompatibleEmbeddingClient,
    chunked_max_similarity,
)
from lineageweave.semantic_spans import (
    TiktokenTokenCodec,
    make_semantic_span_chunker,
)

client = OpenAiCompatibleEmbeddingClient(
    base_url=orchestrator_url,
    api_key=service_token,
    model="text-embedding-3-large",
)
chunker = make_semantic_span_chunker(
    codec=TiktokenTokenCodec("cl100k_base"),
    embedder=client,
)
score, left_span, right_span = chunked_max_similarity(
    client,
    left_text,
    right_text,
    chunker=chunker,
)
```

A deployment may inject another exact `TokenCodec`, including a tokenizer
service owned by `pg-llm-batch`, without changing the packer.

## 13. Evaluation plan

### 13.1 Baselines

1. current paragraph chunker;
2. fixed 800-token window with 100-token overlap; and
3. structure-only semantic spans without dense boundary scoring.

### 13.2 Proposed treatment

Structure + exact token budget + dense adjacency similarity + hierarchical
retrieval.

### 13.3 Corpus

Use synthetic and public/licensed documents that contain:

- single-script prose;
- mixed scripts within one sentence and paragraph;
- CJK text without whitespace;
- right-to-left text;
- translated quotations;
- headings, lists, tables, code, and dialogue;
- one extremely long punctuation-free unit; and
- metadata large enough to test final-payload overflow.

Evaluation labels may describe script composition for analysis. Runtime must
not consume those labels or route on a language classification.

### 13.4 Metrics

- overflow rate;
- Recall@5/10;
- nDCG@10;
- MRR;
- boundary precision/recall/F1 on annotated topic transitions;
- human-rated span coherence;
- context-restoration success;
- duplicate evidence rate;
- embedding tokens and calls per source token;
- p50/p95 indexing latency;
- p50/p95 query latency; and
- storage per document at 3,072/1,536/1,024 dimensions.

### 13.5 Promotion gates

- `overflow_rate == 0` across adversarial tests;
- Recall@10 no worse than current paragraph baseline;
- statistically meaningful improvement over fixed windows on at least one of
  Recall@10 or nDCG@10 without material regression in the other;
- mixed-script slice within five percentage points of the overall retrieval
  score;
- no unit-test network calls; and
- no real organization data in repository fixtures.

## 14. Observability

Emit structured metrics by policy version, not by inferred language:

- `semantic_span_documents_total`
- `semantic_span_units_total`
- `semantic_span_token_count`
- `semantic_span_boundary_score`
- `semantic_span_forced_split_total`
- `semantic_span_provider_fallback_total`
- `semantic_span_payload_rejection_total`
- `semantic_span_embedding_cache_hit_total`
- `semantic_span_index_latency_seconds`

Sample only synthetic or redacted content. Production logs should carry hashes,
counts, span IDs, and policy IDs rather than full text.

## 15. Security, privacy, and governance

- Treat source text as untrusted data, never executable instructions.
- Keep provider credentials in contextual-orchestrator or secret storage.
- Enforce tenant filters before vector search and neighbor expansion.
- Include all metadata in the token guard to prevent an oversized-prefix bypass.
- Hash normalized content for idempotency and audit without logging plaintext.
- Apply retention/deletion to source spans, parent summaries, vectors, caches,
  and evaluation exports together.
- Record model and policy provenance so regulated decisions can be reproduced.
- Do not infer or persist language, ethnicity, nationality, or other sensitive
  traits merely to make segmentation work.

## 16. Delivery plan

### Phase 0 — baseline in this PR

- `semantic_spans.py` core;
- exact-token codec protocol and optional Tiktoken adapter;
- dense-adjacency cache;
- final metadata payload guard;
- adapter to existing `Chunk` interface;
- mixed-script and adversarial unit tests at 100% module coverage; and
- ADR plus this implementation plan.

### Phase 1 — embedding-channel integration

- feature flag: `LINEAGEWEAVE_SEMANTIC_SPANS_ENABLED`;
- batch micro-unit embeddings through contextual-orchestrator;
- policy configuration validation at service startup;
- current paragraph chunker retained for controlled A/B comparison;
- structured metrics and cost counters.

### Phase 2 — persistence and hierarchy

- migrations for the four normalized objects;
- section/document summary generation through contextual-orchestrator;
- parent/neighbor expansion API;
- content-hash incremental reindexing;
- policy-versioned reindex command.

### Phase 3 — evaluation and promotion

- public/synthetic benchmark pack;
- offline report for all baselines and dimension settings;
- canary by tenant/project, not language;
- rollback by policy version;
- default-on only after promotion gates pass.

## 17. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Dense boundary calls increase indexing cost | Embed micro-units in one batch, cache within the document, and reuse leaf vectors where possible. |
| Punctuation segmentation over/under-splits abbreviations | Treat punctuation as a weak structural prior; dense similarity and packing can merge related units. |
| A single unpunctuated unit exceeds the provider limit | Exact token-window fallback guarantees safety. |
| Metadata pushes a safe leaf over the request limit | Count and reject the final rendered payload before HTTP. |
| Short final span loses context | Store parent and bounded neighbor links; do not solve primarily with duplicate overlap. |
| Hosted API cannot provide late chunking | Keep current pre-chunk design; evaluate late chunking only for self-hosted models exposing token representations. |
| Model/tokenizer changes invalidate counts | Version the codec and policy and reindex by content hash. |
| Runtime language inference creates sensitive metadata | No language inference is required or stored by this control path. |

## 18. Definition of done

The capability is production-ready when:

- all promotion gates pass;
- the final request guard is active on every embedding call;
- batch transport and idempotent reindexing are implemented;
- hierarchical persistence and tenant filtering are verified;
- runbooks document provider outage, reindex, rollback, and deletion;
- architecture and API docs link the accepted ADR; and
- released versions update `CHANGELOG.md`, package versions, and deployment
  manifests together.

## References (APA 7th)

Günther, M., Mohr, I., Williams, D. J., Wang, B., & Xiao, H. (2024). *Late chunking: Contextual chunk embeddings using long-context embedding models* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2409.04701

Hearst, M. A. (1997). TextTiling: Segmenting text into multi-paragraph subtopic passages. *Computational Linguistics, 23*(1), 33–64. https://aclanthology.org/J97-1003/

OpenAI. (2026). *Embeddings guide*. OpenAI API documentation. Retrieved August 15, 2026, from https://platform.openai.com/docs/guides/embeddings

OpenAI. (2026). *Embeddings FAQ*. OpenAI Help Center. Retrieved August 15, 2026, from https://help.openai.com/en/articles/6824809-embeddings-faq

OpenAI. (2026). *Text-embedding-3-large model*. OpenAI API documentation. Retrieved August 15, 2026, from https://developers.openai.com/api/docs/models/text-embedding-3-large

The Unicode Consortium. (2025). *Unicode Standard Annex #15: Unicode normalization forms* (Revision 57). https://www.unicode.org/reports/tr15/

The Unicode Consortium. (2025). *Unicode Standard Annex #29: Unicode text segmentation* (Revision 47). https://www.unicode.org/reports/tr29/
