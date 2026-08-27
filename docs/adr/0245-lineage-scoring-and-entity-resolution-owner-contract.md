# ADR 0245 — Lineage scoring and entity resolution require owner artifacts

**Decision status:** Accepted

**Date:** 2026-08-26
**Amends:** ADR 0026, ADR 0064, ADR 0084, and ADR 0208

## Context

ADR 0208 freezes local numerical computation as migration debt, but its audit
does not name every active path. Protected `main` still executes the following
Python decisions during ordinary reconstruction and ingestion:

- `lineageweave/channels.py` computes an inverse elapsed-day score, a numeric
  secondary-key score, and `difflib.SequenceMatcher` text similarity;
- `lineageweave/reconstruct.py` renormalizes weights, limits candidates to the
  latest 50 records, applies a fixed `0.3` score floor, and invokes weighted
  fusion before selecting a parent; and
- `lineageweave/corporate_hierarchy_resolution.py` deletes a fixed suffix
  vocabulary, computes `SequenceMatcher` similarity, and applies a fixed `0.6`
  catalog-binding threshold.

Those paths affect product facts or evidence selection. They are not merely
display formatting or operational resource accounting. The cited record-
linkage literature supports an explicit uncertain outcome, but it does not
validate these particular constants or Python string-similarity rules.

Current ecosystem contracts do not provide a complete replacement. TEPP's
published LineageWeave project-history exchange returns temporal association,
not candidate-parent scores. RankWeave owns fusion and retrieval, but its
current public contract does not return a Rust-computed Event-Lineage edge
artifact or organization-identity decision. contextual-orchestrator owns
embedding transport and model orchestration, not catalog identity. Keyverse
owns account identity and is not implicitly assigned corporate-master entity
resolution.

Open PR #704 at audited head `ea6c5c8e9819590dfbc058344435122584947f6e`
publishes a useful external evidence envelope, but its analysis implementation
imports `_best_parent` and `active_weights`, computes candidate-window counts
and per-channel contributions, and applies caller policy score floors. It is
therefore a consumer-contract delivery, not the owner-compute replacement
required by this decision; its local arithmetic must not be cited as closing
this gap.

## Decision

1. **No local scoring extension.** The three named modules are frozen migration
   debt. No new decay, normalization, token overlap, similarity algorithm,
   candidate-order rule, score floor, threshold, or numeric fallback may be
   added. Tests may characterize legacy behavior but may not call it calibrated,
   paper-grounded, or release-compliant.
2. **Event-Lineage owner envelope.** Replacement activates only from a
   versioned owner result containing:
   - contract and result-schema versions;
   - immutable input snapshot digest and knowledge cutoff;
   - every considered record id and the evidence-unit references authorized by
     LineageWeave before submission;
   - selected parent id or an explicit abstention;
   - separate temporal, grouping, semantic, and adjudication evidence with
     availability status;
   - owner model/method version, convergence or completion status, uncertainty
     where the method defines it, and deterministic result digest; and
   - an explicit non-causal classification.
   TEPP owns calibrated temporal/event criterion evidence. RankWeave may own the
   Rust-backed candidate ranking/fusion artifact after its PRD and API accept
   that responsibility. LineageWeave validates and persists the envelope; it
   never recomputes, renormalizes, thresholds, or repairs it.
3. **Corporate-entity resolution envelope.** No existing repository is assigned
   this construct by inference. An owning repository must first accept a PRD/ADR
   and publish a versioned result containing the input snapshot digest, bounded
   candidate catalog ids, source/alias evidence references, `unique`/`miss`/`tie`
   outcome, selected catalog id only for `unique`, method/model version,
   uncertainty or review status, and result digest. Until then, no new automatic
   similarity binding path may activate.
4. **Resource limits are not evidence.** A bounded request may cap records or
   bytes before an owner call, but recency, truncation order, or a fixed window
   must not decide scientific relevance. The request records any truncation and
   the result remains incomplete rather than silently treating excluded
   candidates as negative evidence.
5. **Deletion sequence.** After exact owner contracts land and pass synthetic
   recovery/equivalence tests, separate consumer PRs add strict adapters and
   persisted provenance. Only then do deletion PRs remove the corresponding
   functions and constants. Missing, malformed, stale-digest, incomplete, or
   unavailable owner results produce no edge or catalog binding.

## Consequences

- Existing runtime behavior remains honestly labeled migration debt rather
  than being moved unchanged to another repository.
- LineageWeave cannot claim the affected reconstruction or automatic catalog
  binding paths satisfy its product boundary until their local implementation
  is deleted.
- Exact equality, sorting, authorization, persistence, and UI projection may
  remain local when they do not manufacture a score or identity decision.
- The customer sees an unavailable or review-needed state instead of a guessed
  lineage edge or organization identity when the owner artifact is absent.

## References — APA 7th

Bhattacharya, I., & Getoor, L. (2007). Collective entity resolution in
relational data. *ACM Transactions on Knowledge Discovery from Data, 1*(1),
Article 5. https://doi.org/10.1145/1217299.1217304

Fellegi, I. P., & Sunter, A. B. (1969). A theory for record linkage. *Journal
of the American Statistical Association, 64*(328), 1183–1210.
https://doi.org/10.2307/2286061
