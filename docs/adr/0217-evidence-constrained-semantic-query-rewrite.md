# ADR 0217: Evidence-constrained semantic query rewriting

## Status

Accepted

## Context

Global Ask already fuses embedding and persisted semantic/Knowledge Graph
candidate lists through RankWeave. Its database-native evidence channel passed
the complete conversational question to PostgreSQL
`websearch_to_tsquery('simple', ...)`; retained generic words could therefore
turn a valid semantic fact into a miss. Local stop-word lists, term weights, or
language-specific rules would be uncalibrated heuristics.

Ma et al. (2023) show that query rewriting can improve retrieval-augmented
language-model retrieval. Their result supports a rewrite stage, but it does
not authorize LineageWeave to invent synonyms, translations, or factual
expansions. ADR 0076 also assigns model discovery, structured synthesis, and
reasoning allocation to contextual-orchestrator.

## Decision

Before acquiring a database connection, the asynchronous Global Ask worker may
ask contextual-orchestrator for a strict structured list of retrieval phrases.
Every returned phrase must be a non-empty, exact substring of the submitted
question. The client rejects invented terms, translations, case changes,
non-text values, empty lists, and more than 32 phrases.

Each accepted phrase becomes its own parameterized PostgreSQL
`websearch_to_tsquery('simple', phrase)`. Matching candidates are unioned and
deduplicated before the existing authorization, eligibility, event-time,
knowledge-cutoff, bounded-channel, and RankWeave fusion boundaries. No phrase
receives a local score or weight.

An unavailable or invalid rewrite retains the original complete question. It
does not fabricate a phrase, silently broaden access, or disable the embedding
channel. The fallback is an honest lower-recall compatibility path.

## Consequences

- Natural-language framing no longer has to occur in persisted ontology or
  semantic evidence for an exact question phrase to nominate that evidence.
- The rewrite cannot add a fact absent from the user's question.
- Provider latency stays outside the asyncpg pool, and Global Ask remains an
  asynchronous job rather than an interactive blocking request.
- Runtime multilingual recall remains a release-evidence requirement; unit
  tests prove the contract and authorization-preserving SQL shape only.

## References

Ma, X., Gong, Y., He, P., Zhao, H., & Duan, N. (2023). Query rewriting in
retrieval-augmented large language models. In *Proceedings of the 2023
Conference on Empirical Methods in Natural Language Processing* (pp.
5303–5315). Association for Computational Linguistics.
https://doi.org/10.18653/v1/2023.emnlp-main.322

PostgreSQL Global Development Group. (2026). *Text search functions and
operators*. https://www.postgresql.org/docs/current/functions-textsearch.html
