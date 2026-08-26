# ADR 0242: Private content semantic-coverage audit

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
   `conduct` mode. Every accepted batch requires a multi-step trace. The model
   receives a deterministic public ontology contract containing each governed
   term's IRI, RDF kind, labels, comments, domain, range, and SKOS scheme; local
   names alone are not semantic evidence. Coverage evaluates schema
   expressibility: source-specific names and values are instance data when a
   supplied class/property represents them, not missing private vocabulary.
3. The model classifies only governed semantic dimensions; it does not decide
   coverage or select ontology IRIs. The caller accepts a batch only when JSON,
   input count, item count, ordered indexes, and non-empty unique governed
   dimension codes validate. It then deterministically resolves each dimension
   against the current ontology contract: present governed class/property IRIs
   become supporting evidence, while a dimension with no current term remains
   missing. The contract parses the published PROV-O support
   profile with the primary ontology and includes `rdfs:subClassOf` and
   `rdfs:subPropertyOf`. It also reuses the runtime's canonical 30 PROV-O class,
   50 property, and qualification-table registries, so standard semantics are
   present in the audit rather than reduced to imports or local mappings.
   This separation prevents an invented abbreviation or near-match from
   becoming a new ontology term while retaining IRI evidence after validation.
   Person/actor meaning is a governed dimension distinct from organization role;
   collapsing the two would hide whether the ontology identifies an actor or only
   an organizational function. Project/initiative meaning is likewise distinct
   from product/service meaning because the former denotes organized work while
   the latter denotes an offering or deliverable.
4. No retry repairs, lexical rules, inferred categories, source values,
   identifiers, or row-level outputs are persisted or printed. Any malformed,
   incomplete, single-agent, or unavailable result fails the run.
5. Only complete non-identifying aggregates may enter repository documents.
   A sample audit describes the sample, never the full corpus.
   The aggregate source audit may additionally compare distinct caller-selected
   source and semantic-layer keys. It reports matched and one-sided key counts
   only; identifiers and values never enter output or repository artifacts.
   When a caller supplies a semantic-edge table, the audit also reports only
   aggregate `observed`, `inferred`, `predicted`, ungoverned-status, and
   evidence-reference counts. An observed edge without an evidence reference
   fails the source-evidence boundary. An inferred or predicted edge may lack a
   direct source evidence reference, but that does not make it provenance-free:
   its generation or derivation still requires the normalized PROV-O resource,
   assertion, and qualification schema from ADR 0011. The audit therefore
   reports deployment of that complete schema separately and never relabels an
   inference reason, mapping source, confidence, or deterministic identifier as
   source evidence or qualified provenance.
6. Missing-dimension counts do not themselves authorize new private ontology
   terms. Event/activity candidates must first reconcile with PROV-O;
   temporal candidates with OWL-Time; and observed property, asset, system,
   or feature-of-interest candidates with the current SOSA/SSN edition. A
   source-grounded normalized fact and qualified provenance remain mandatory.
7. A probability-sample audit additionally requires a versioned caller-supplied
   sample manifest: a complete population/frame size, simple or stratified
   random design, exact inclusion-probability numerator/denominator and frame
   digest for every
   stratum, ordered selected-unit token digests bound to their strata, a
   canonical selection-manifest digest, and
   `provider_failures_retained=true`.
   Deterministic windows, convenience samples, unknown inclusion probabilities,
   and replacement of failed items are pipeline evidence only.
8. NIST/SEMATECH's proportion design begins with
   `n0 = z² p(1-p) / delta²`; sampling without replacement applies
   `n = n0 / (1 + (n0 - 1) / N)`. Stratified designs determine sample size per
   stratum. LineageWeave neither evaluates those equations nor derives sample
   weights: a versioned, SHA-256-bound `ContextualWisdomLab/fast-mlsirm` Rust
   artifact owns that arithmetic. Manifest contract v3 carries each stratum's
   exact `(n_h, N_h)` ratio rather than a rounded decimal. The audit replays the complete Rust-owned
   design artifact and requires its population, ordered stratum populations,
   total sample size, stratum allocations, and Rust-attested exact inclusion
   ratios to match the separately bound selection manifest. The artifact accepts no caller hash or selected
   membership. For a complete one-stratum SRSWOR audit, the immutable
   `fast-mlsirm.achieved-proportion.v1` artifact binds that design artifact and
   attests the sample-proportion estimand, SRSWOR design variance, and exact
   Wang/Konijn equal-tailed hypergeometric interval. The script additionally
   binds the terminal artifact, selection-manifest digest, ontology SHA-256,
   aggregate verdict counts, and trace-count bounds into one audit SHA-256.
   The same aggregate-only envelope carries a validated PROV-O graph: the
   audit activity `prov:used` the selection manifest, Rust design, completed
   attempt, ontology, and Rust terminal entities; the audit entity
   `prov:wasGeneratedBy` that activity and `prov:wasDerivedFrom` all five
   inputs. The completed attempt must match the selection, design, ontology,
   and accepted sample count before terminal evidence can exist. Resource IRIs are content-addressed
   URNs, so no private source identifier enters the repository artifact.
   Only that complete chain sets `corpus_inference_available=true`.
   Stratified terminal inference remains unavailable rather than receiving an
   invented variance or interval. Caller-recomputed hashes do not
   establish Rust provenance or authorize corpus inference. Confidence,
   margin, prior-proportion, or interval fields are not accepted as proof when
   no immutable owner artifact attests their computation.
9. Any provider, transport, trace, parse, or item failure invalidates the whole
   declared probability sample. The selected item remains in the denominator
   and must be retried in place; it is never dropped or replaced by another
   record. Only a zero-failure complete run emits a coverage aggregate. The
   failed execution itself is not erased: an owner-only aggregate attempt
   artifact records the accepted-item count, failed batch index, bounded error
   class, and a content-addressed PROV-O graph showing that the attempt activity
   used the selection manifest, Rust design artifact, and ontology. This is
   execution provenance, not a partial coverage result, and therefore never
   sets `corpus_inference_available` or persists row-level verdicts. Each
   provider call runs behind a terminable process boundary so the declared
   timeout is a wall-clock deadline, not merely a socket inactivity timeout;
   a peer that keeps a connection active cannot leave the attempt indefinitely
   `in_progress`. Because process spawning does not inherit request context,
   every provider call carries the same non-identifying audit session id,
   derived from the selection, design, and ontology hashes, through the HTTP
   header, request metadata, local telemetry, and attempt artifact, so
   orchestration trace and execution PROV stay correlated.
10. The model receives the locally validated semantic-dimension support
    profile, not the entire ontology inventory. It classifies source meaning
    into governed dimensions but never selects terms or decides coverage.
    LineageWeave retains the complete ontology/PROV registry validation and
    binds the complete ontology bytes by SHA-256. This keeps each request below
    gateway payload limits without weakening the ontology evidence boundary.
11. Requests use contextual-orchestrator's provider-neutral
    `orchestrator/auto` route. LineageWeave does not name or rank a provider
    model; discovery, agent-pool construction, and routing remain upstream as
    required by ADR 0076.
12. Every request supplies a strict JSON Schema whose `input_count`, item-array
    minimum/maximum length, index bounds, allowed dimensions, and closed object
    fields are bound to that batch. contextual-orchestrator retains
    multi-agent synthesis, schema validation, and repair; LineageWeave still
    revalidates exact ordered indexes and discards the whole declared sample on
    any transport, schema, trace, or cardinality failure.
13. The current corpus acceptance audit declares a two-sided 95% confidence
    level, 5-percentage-point margin, and the NIST conservative unknown-
    proportion input `p=0.5` before selection. For the current 43,814-record
    eligible frame, the Rust finite-population design yields 381 SRSWOR units.
    These are explicit audit acceptance inputs, not estimated channel weights;
    changing them requires a new design artifact and a new selection manifest.

## Consequences

An HTTP 200 can no longer turn a partial classification into coverage evidence.
The audit remains unavailable when contextual-orchestrator cannot complete all
batches, preserving failures in the declared denominator instead of silently
shrinking the sample. The observed 80-record result remains exploratory pipeline
acceptance evidence. The Rust design artifact proves sample-size,
finite-population-correction, and allocation provenance only. A complete
one-stratum SRSWOR audit becomes corpus inference evidence only when its Rust
terminal artifact and aggregate audit identity also validate. This does not
turn the point estimate into certainty: an all-success sample retains a lower
exact confidence bound below one unless the sample is a census.

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

Wang, W. (2015). Exact optimal confidence intervals for hypergeometric
parameters. *Journal of the American Statistical Association, 110*(512),
1491–1499. https://doi.org/10.1080/01621459.2014.966191
