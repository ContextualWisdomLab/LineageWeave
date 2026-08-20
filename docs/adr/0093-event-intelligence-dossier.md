# ADR 0093: Compose Event Intelligence without collapsing scientific authorities

- **Status:** Accepted
- **Date:** 2026-08-20
- **Decision owners:** LineageWeave product and scientific integration maintainers
- **Related:** ADR 0003, ADR 0004, ADR 0016, ADR 0034, TEPP ADR 0011

## Context

The Buyer-surface stack ending at PR #264 makes LineageWeave evidence easier to
reach, but the product still exposes its event-intelligence inputs as separate
features:

- the LineageWeave knowledge graph computes an evidence-backed neighborhood;
- the LineageWeave ontology provides semantic identifiers and labels;
- TEPP owns temporal-event and topic-model scientific artifacts;
- fast-mlsirm owns calibrated psychometric estimates and their uncertainty;
- contextual-orchestrator supplies bounded model routing and LLM judgment;
- source posts and model artifacts carry independent provenance.

No versioned object required all of these channels to share the same immutable
snapshot, knowledge cutoff, evidence identities, ontology references, method
versions, uncertainty, and content digests. A UI or downstream integrator could
therefore join unrelated clocks, show an LLM verdict as though it were a
psychometric score, or omit an unavailable scientific channel without saying
that it was unavailable.

That gap is architectural rather than cosmetic. Adding a single blended
"event score" would hide disagreements and transfer scientific authority to the
composer. Copying TEPP or fast-mlsirm calculations into LineageWeave would also
break the existing repository boundaries.

## Decision

LineageWeave publishes **Event Intelligence Dossier v1** as an evidence-bound,
deterministic composition contract.

The dossier is a buyer-facing read artifact, not a new estimator. It contains:

1. a source snapshot identity and six distinct clocks: event start/end,
   assertion, document, availability, and knowledge cutoff;
2. versioned ontology references for the event and graph assertions;
3. immutable evidence references with source authority, URI, digest,
   availability time, and recorded time;
4. an evidence-backed LineageWeave graph neighborhood and method-labelled
   relevance with uncertainty;
5. an optional TEPP artifact that must use the same snapshot and cutoff and
   retain TEPP's model/engine/digest identity;
6. an optional fast-mlsirm artifact that retains its construct scale, estimate,
   standard error, model/engine version, and digest;
7. an optional contextual-orchestrator verdict that cites evidence and records
   trace, operation, policy, prompt digest, verdict, confidence, and rationale;
   the live pair-adjudication client requests this as strict JSON, JSON-encodes
   candidate labels as untrusted evidence, requests the orchestration trace, and
   fails closed rather than regex-extracting a number from free-form text;
8. buyer-facing claims whose complete supporting evidence IDs are explicit;
9. a SHA-256 over the canonical dossier payload.

The JSON Schema is `schemas/event_intelligence_dossier_v1.schema.json`. The
runtime implementation is `lineageweave.event_intelligence`; the validator CLI
is `lineageweave-validate-event-intelligence`.

## Authority rules

| Channel | What it may assert | What it may not replace |
|---|---|---|
| LineageWeave knowledge graph | graph neighborhood and graph relevance | TEPP topic inference or psychometric calibration |
| LineageWeave ontology | semantic identifiers and relation meaning | observed source evidence |
| TEPP | temporal/topic artifact under its own model contract | LineageWeave authorization or source-of-record data |
| fast-mlsirm | calibrated estimate and uncertainty on a named scale | TEPP temporal/topic truth |
| contextual-orchestrator | evidence-bounded supported/refuted/insufficient verdict | numerical relevance or psychometric measurement |
| source evidence | what was available and recorded | model-derived inference |

The composer never averages these outputs into one number. A missing TEPP,
fast-mlsirm, or orchestrator channel is serialized as
`{"status_code":"unavailable"}` rather than a zero, null score, or fabricated
fallback.

## Temporal rules

Every evidence item must satisfy:

```text
available_time <= knowledge_cutoff
```

The TEPP artifact must match both `source_snapshot_id` and
`knowledge_cutoff`. Event time may precede assertion, document, or availability
time; those clocks remain separate so retrospective reports do not leak into a
historical model.

The ontology profile distinguishes a forward transition from a retrospective
report. A later document may report an earlier event, but that reporting edge
must not be treated as a forward event-state transition.

## Semantic profile

`docs/ontology/event-intelligence-profile.ttl` specializes existing
LineageWeave vocabulary with:

- OWL-Time temporal entities and intervals;
- PROV-O entities, activities, derivation, and primary-source provenance;
- typed event episode, evidence bundle, knowledge-graph projection,
  temporal-topic artifact, psychometric artifact, judge decision, grounded
  claim, and dossier classes;
- method, version, estimate, uncertainty, digest, verdict, and confidence
  properties.

PostgreSQL and the upstream products remain the systems of record. The profile
is an interchange/read-model vocabulary, not a second mutable database.

## Validation and failure behavior

Runtime reconstruction rejects:

- unknown or missing fields;
- non-UTF-8 or invalid JSON in the CLI;
- future evidence relative to the cutoff;
- unknown evidence IDs;
- graph edges whose endpoints are absent;
- mismatched TEPP snapshot or cutoff;
- orchestrator attempts to add a psychometric score;
- free-form, duplicated-field, non-finite, out-of-range, or malformed lineage
  adjudication output;
- unsupported channel states;
- altered payloads whose dossier digest no longer matches.

Production statement and branch coverage for the two new dossier modules and
the hardened adjudication client is 100%. The ontology, schema shape, canonical example, CLI receipt, and negative
contracts have dedicated regression tests.

## Consequences

### Positive

- Buyers receive one inspectable event-intelligence artifact rather than a set
  of unrelated widgets.
- Disagreement between graph, topic, psychometric, and judge channels remains
  visible and auditable.
- TEPP and fast-mlsirm can evolve behind their own versioned contracts without
  LineageWeave reimplementing their mathematics.
- The same dossier can back an API, an export, a buyer UI, and downstream MCP
  context while preserving exact values and evidence.
- Historical replay is deterministic when the source artifacts and versions
  are retained.

### Costs and limitations

- This ADR defines composition and validation, not a live TEPP HTTP service or
  a new fast-mlsirm estimator.
- A backend projection and buyer UI still need to select authorized artifacts
  and render the dossier.
- Causal claims remain out of scope unless a separately validated model and
  claim type support them.
- An LLM verdict remains a fallible judgment channel and must be calibrated and
  compared with human or statistical evidence for high-stakes use.

## Rejected alternatives

### One blended event-relevance score

Rejected because the component scales and authorities are not interchangeable,
and a weighted average would obscure uncertainty and disagreement.

### Copy TEPP topic or fast-mlsirm estimation into LineageWeave

Rejected because production numerical authority belongs in those repositories,
and duplicated implementations would drift.

### Let contextual-orchestrator synthesize the complete artifact without a
strict schema

Rejected because source text is untrusted, free-form output is not a durable
contract, and an LLM must not decide the scientific acceptance boundary.

### Store only prose with citations

Rejected because buyers and downstream systems need machine-checkable clocks,
method versions, uncertainty, ontology identifiers, and content digests.

## References

See `docs/doctoring/EVENT_INTELLIGENCE_REFERENCES.md` for APA 7th references
and requirement traceability.
