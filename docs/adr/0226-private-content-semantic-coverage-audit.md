# ADR 0226: Private content semantic-coverage audit

**Status:** Accepted
**Date:** 2026-08-26
**Extends:** [ADR 0001](0001-demo-identity-and-data-boundary.md),
[ADR 0004](0004-knowledge-graph-ontology.md), and
[ADR 0089](0089-private-real-data-runtime-boundary.md)

## Context

Schema availability does not prove that the ontology expresses the material
meaning of source content. A first runtime request submitted 100 private titles
but returned a claimed sample size of 60. The transport had succeeded, yet the
semantic result was unusable because neither the model nor the caller enforced
cardinality. A later 80-record deterministic-window run proved only that the
pipeline could preserve ordered outputs; it had neither a probability frame nor
known inclusion probabilities and therefore cannot estimate corpus coverage.
Repository artifacts must not retain the private titles.

## Decision

1. `scripts/audit_source_content_semantics.py` reads a caller-owned query that
   returns exactly `selection_token, content_text` in manifest order and exactly
   the declared sample. Each runtime-only owner-issued opaque token must hash to
   the corresponding manifest membership digest; neither tokens nor digests are
   sent to contextual-orchestrator or printed.
2. Content crosses only the configured contextual-orchestrator boundary in
   `conduct` mode. Every accepted batch requires a multi-step trace.
3. The caller accepts a batch only when JSON, input count, item count, ordered
   indexes, booleans, and governed missing-dimension codes all validate.
4. No retry repairs, lexical rules, inferred categories, source values,
   identifiers, or row-level outputs are persisted or printed. Any malformed,
   incomplete, single-agent, or unavailable result fails the run.
5. Only complete non-identifying aggregates may enter repository documents.
   A sample audit describes the sample, never the full corpus.
6. Missing-dimension counts do not themselves authorize new private ontology
   terms. Event/activity candidates must first reconcile with PROV-O;
   temporal candidates with OWL-Time; and observed property, asset, system,
   or feature-of-interest candidates with the current SOSA/SSN edition. A
   source-grounded normalized fact and qualified provenance remain mandatory.
7. A corpus inference additionally requires a versioned caller-supplied sample
   manifest: a complete population/frame size, simple or stratified random
   design, known inclusion probability and frame digest for every stratum,
   explicit confidence and margin targets, an expected proportion backed by a
   named prior-evidence reference, ordered selected-unit token digests bound to
   their strata, and `provider_failures_retained=true`.
   Deterministic windows, convenience samples, unknown inclusion probabilities,
   and replacement of failed items are pipeline evidence only.
8. NIST/SEMATECH's proportion design begins with
   `n0 = z² p(1-p) / delta²`; sampling without replacement applies
   `n = n0 / (1 + (n0 - 1) / N)`. Stratified designs determine sample size per
   stratum. LineageWeave neither evaluates those equations nor derives sample
   weights: a versioned, SHA-256-bound `ContextualWisdomLab/fast-mlsirm` Rust
   artifact owns that arithmetic. The artifact input digest binds the declared
   design and the output digest binds the ordered selected-unit manifest; this
   script validates only those hashes, opaque owner tokens, and exact item
   cardinality.
9. Any provider, transport, trace, parse, or item failure invalidates the whole
   declared probability sample. The selected item remains in the denominator
   and must be retried in place; it is never dropped or replaced by another
   record. Only a zero-failure complete run emits a coverage aggregate.

## Consequences

An HTTP 200 can no longer turn a partial classification into coverage evidence.
The audit remains unavailable when contextual-orchestrator cannot complete all
batches, preserving failures in the declared denominator instead of silently
shrinking the sample. The observed 80-record result remains pipeline acceptance
evidence only until an independently generated probability-sample manifest and
its Rust owner artifact exist.

## References

Cox, S., & Little, C. (Eds.). (2022). *Time ontology in OWL*. World Wide Web
Consortium. https://www.w3.org/TR/owl-time/

Cox, S. J. D., Lefrançois, M., Warren, R., Atkinson, R., Moreira de Sousa, L.,
Schleidt, K., Grellet, S., & Janowicz, K. (Eds.). (2026). *Semantic Sensor
Network Ontology—2023 edition* (Working Draft). World Wide Web Consortium &
Open Geospatial Consortium. https://www.w3.org/TR/vocab-ssn-2023/

Australian Bureau of Statistics. (2022). *Basic survey design: Sample design*.
https://www.abs.gov.au/websitedbs/D3310114.nsf/home/Basic%20Survey%20Design%20-%20Sample%20Design

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

National Institute of Standards and Technology. (n.d.). *Selecting sample
sizes*. In *NIST/SEMATECH e-handbook of statistical methods*.
https://www.itl.nist.gov/div898/handbook/ppc/section3/ppc333.htm

National Institute of Standards and Technology. (n.d.). *Confidence limits*.
In *NIST/SEMATECH e-handbook of statistical methods*.
https://www.itl.nist.gov/div898/handbook/prc/section2/old.prc271.htm
