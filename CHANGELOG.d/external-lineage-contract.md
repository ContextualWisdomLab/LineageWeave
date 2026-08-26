# External email/project lineage contract

- Add a strict, versioned external analysis contract for future Naruon and separately governed consumer use.
- Export immutable request/result types, strict parsing, canonical serialization, deterministic digests, stable errors, and the store-agnostic `analyze_external_lineage` package entry point.
- Accept only bounded caller-authorized opaque evidence references; no provider credentials, mailbox access, persistence, provider mutation, or direct application-database integration is introduced.
- Preserve caller-observed RFC/provider/manual parent relations separately from inferred reconstructed continuation.
- Exclude caller-observed children from alternative inferred-parent scoring, optional model disclosure, and inferred-pair budget while retaining them as candidate history for later records.
- Enforce available-time knowledge cutoffs and disclose excluded evidence without substituting later facts.
- Reject explicit-parent cycles and candidate-pair work above the caller-approved limit before optional LLM/provider activity.
- Expose exact active channel scores, weights, contributions, LLM availability state, proposed project groupings, and deterministic result digests.
- Require a provenance-bearing fast-mlsirm channel-weight estimate for inferred edges; without it, return observed edges plus an explicit unavailable limitation.
- Add JSON Schema Draft 2020-12, union-free ADR 0239, APA 7th doctoring, and focused TDD coverage.
