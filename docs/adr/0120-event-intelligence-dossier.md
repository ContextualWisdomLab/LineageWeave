# ADR 0120: Compose Event Intelligence without collapsing scientific or provenance authorities

- **Status:** Accepted; amended 2026-08-21
- **Date:** 2026-08-20
- **Decision owners:** LineageWeave product and scientific integration maintainers
- **Related:** ADR 0003, ADR 0004, ADR 0016, ADR 0034, ADR 0065, ADR 0074, ADR 0079, TEPP ADR 0011

## Context

The Buyer-surface stack ending at PR #264 makes LineageWeave evidence easier to
reach, but the product still exposes its event-intelligence inputs as separate
features:

- the LineageWeave knowledge graph computes an evidence-backed neighborhood;
- the LineageWeave ontology provides semantic identifiers and labels;
- TEPP owns temporal-event and topic-model scientific artifacts;
- fast-mlsirm owns calibrated psychometric estimates and their uncertainty;
- contextual-orchestrator supplies bounded model routing and LLM judgment; and
- source posts and model artifacts carry independent provenance.

No versioned object required all of these channels to share the same immutable
snapshot, knowledge cutoff, evidence identities, ontology references, method
versions, uncertainty, and content digests. A UI or downstream integrator could
therefore join unrelated clocks, show an LLM verdict as though it were a
psychometric score, or omit an unavailable scientific channel without saying
that it was unavailable.

The first ontology profile correctly treated the dossier as a `prov:Entity`,
but also made `usesEvidenceBundle` a subproperty of `prov:used` with the dossier
as its domain. Because PROV-O defines `prov:used` for an activity using an
entity, ordinary RDFS reasoning would infer that the dossier entity was also a
`prov:Activity`. The same profile made the direct Post-to-EventEpisode
`evidencesEvent` edge a subproperty of `prov:influenced`, which could be read as
the later source document influencing the real-world event rather than
supporting an assertion about it.

Those are semantic-model defects, not cosmetic vocabulary choices. They would
make standards-aware consumers infer roles the product does not intend.

## Decision

LineageWeave publishes **Event Intelligence Dossier v1** as an evidence-bound,
deterministic composition contract. The wire contract remains version 1 because
this correction occurs before the profile is released on protected `main`.

### Dossier entity and generation activity

The dossier is a buyer-facing read artifact and a `prov:Entity`; it is not an
estimator or an activity. A separate `DossierGenerationActivity`, subclassed
from `prov:Activity`, represents deterministic composition.

```text
DossierGenerationActivity
  -- usesEvidenceBundle / prov:used --> EvidenceBundle
  -- usesEventAssertion / prov:used --> EventAssertion
  -- generatesDossier / prov:generated --> EventIntelligenceDossier
```

This preserves the PROV-O domain and range contract instead of relying on a
single resource to be both the process and its output.

### Event, assertion, and source separation

A source post is not the event and is not asserted to have caused the event.
The profile therefore introduces `EventAssertion` as a first-class
`prov:Entity`:

```text
EventAssertion
  -- supportedBySource / prov:wasDerivedFrom --> LineageWeave Post
  -- assertsEvent --> EventEpisode
```

The existing `evidencesEvent` Post-to-EventEpisode relation remains available
as a bounded Buyer read-model convenience edge. It is deliberately **not** a
subproperty of `prov:influenced`, does not transfer source authority to an
inference, and has no causal meaning. Producers that publish full RDF should
retain the mediating assertion; bounded Buyer graph projections may publish the
convenience edge together with the same evidence identifiers.

### Multi-clock temporal semantics

The dossier keeps six distinct clocks: event start/end, assertion, document,
availability, and knowledge cutoff. Exact RFC 3339 values remain in the JSON
contract and corresponding RDF datatype properties. The profile additionally
uses OWL-Time resources:

- an `EventEpisode` has exactly one temporal extent represented as a
  `time:Interval` in the published SHACL profile;
- assertion, document, availability, and cutoff clocks may be represented as
  `time:Instant` resources; and
- forward transitions remain distinct from retrospective reporting.

A later document may describe an earlier event, but that reporting relation
must never become a reverse state transition.

### Versioning and imports

`docs/ontology/event-intelligence-profile.ttl` declares a stable ontology IRI,
`owl:versionIRI` for profile 1.0.0, and metadata imports for the LineageWeave
base ontology, PROV-O, and OWL-Time. Runtime code and tests parse committed
artifacts only and do not dereference imports over the network.

### SHACL interchange constraints

`docs/ontology/event-intelligence-profile.shacl.ttl` publishes closed-world
constraints for the semantic boundaries that OWL/RDFS alone should not be
expected to reject:

- one evidence bundle and one generated dossier per generation activity;
- one asserted event and at least one source per event assertion;
- one OWL-Time interval per event episode;
- required assertion, document, event-start, and knowledge-cutoff values; and
- class constraints for PROV entities/activities and OWL-Time instants/intervals.

The repository tests parse and inspect both the ontology and the SHACL graph.
The production JSON validator remains authoritative for the current JSON wire
artifact; the SHACL document is the standards-based RDF validation contract for
external graph consumers.

## Dossier contents

The dossier contains:

1. a source snapshot identity and the six distinct clocks;
2. versioned ontology references for event and graph assertions;
3. immutable evidence references with source authority, URI, digest,
   availability time, and recorded time;
4. an evidence-backed LineageWeave graph neighborhood and method-labelled
   relevance with uncertainty;
5. an optional TEPP artifact that uses the same snapshot and cutoff and retains
   TEPP model, engine, and digest identity;
6. an optional fast-mlsirm artifact that retains its construct scale, estimate,
   standard error, model, engine, and digest identity;
7. an optional contextual-orchestrator verdict that cites evidence and records
   trace, operation, policy, prompt digest, verdict, confidence, and rationale;
8. buyer-facing claims whose complete supporting evidence IDs are explicit;
   and
9. a SHA-256 over the RFC 8785 JCS canonical dossier payload after removing
   `dossier_sha256`.

The JSON Schema is `schemas/event_intelligence_dossier_v1.schema.json`. The
runtime implementation is `lineageweave.event_intelligence`; the validator CLI
is `lineageweave-validate-event-intelligence`.

## Authority rules

| Channel | What it may assert | What it may not replace |
|---|---|---|
| LineageWeave knowledge graph | Graph neighborhood and graph relevance | TEPP topic inference or psychometric calibration |
| LineageWeave ontology | Semantic identifiers and relation meaning | Observed source evidence |
| TEPP | Temporal/topic artifact under its own model contract | LineageWeave authorization or source-of-record data |
| fast-mlsirm | Calibrated estimate and uncertainty on a named scale | TEPP temporal/topic truth |
| contextual-orchestrator | Evidence-bounded supported/refuted/insufficient verdict | Numerical relevance or psychometric measurement |
| source evidence | What was available and recorded | Model-derived inference or real-world causation |

The composer never averages these outputs into one number. A missing TEPP,
fast-mlsirm, or orchestrator channel is serialized as exactly
`{"status_code":"unavailable"}` rather than a zero, null score, or fabricated
fallback.

## Temporal and validation rules

Every evidence item must satisfy:

```text
available_time <= knowledge_cutoff
```

The TEPP artifact must match both `source_snapshot_id` and
`knowledge_cutoff`. Event time may precede assertion, document, or availability
time; those clocks remain separate so retrospective reports do not leak into a
historical model.

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
- unsupported channel states; and
- altered payloads whose dossier digest no longer matches.

The ontology tests additionally reject a return to a dossier-domain
`prov:used`, a Post-to-Event PROV influence, a generic temporal-entity range,
or an unversioned/unimported profile.

## Consequences

### Positive

- Standards-aware consumers no longer infer that a dossier entity is also its
  generation activity.
- A source document supports an assertion about an event instead of being
  represented as an influence on that real-world event.
- Buyers receive one inspectable event-intelligence artifact rather than a set
  of unrelated widgets.
- Disagreement between graph, topic, psychometric, and judge channels remains
  visible and auditable.
- TEPP and fast-mlsirm can evolve behind their own versioned contracts without
  LineageWeave reimplementing their mathematics.
- JSON consumers retain the strict existing contract while RDF consumers gain
  versioned imports and SHACL constraints.

### Costs and limitations

- Full RDF exchange contains an additional assertion node and generation
  activity that compact Buyer graph projections may omit.
- Publishing SHACL shapes does not turn the current JSON runtime into a generic
  RDF store or SPARQL service.
- This ADR defines composition and validation, not a live TEPP HTTP service or
  a new fast-mlsirm estimator.
- A backend projection and Buyer UI still need to select authorized artifacts
  and render the dossier.
- Causal claims remain out of scope unless a separately validated model and
  claim type support them.
- An LLM verdict remains a fallible judgment channel and must be calibrated and
  compared with human or statistical evidence for high-stakes use.

## Rejected alternatives

### Treat the dossier as both Entity and Activity

Rejected because `prov:used` and `prov:generated` describe activity behavior.
Using them directly from the dossier makes reasoners infer an unintended
activity type and conflates a process with its output.

### Make the source post influence the event episode

Rejected because a report can be created after the event and may only support
an assertion about it. A generic PROV influence edge is too broad and invites a
causal reading the product cannot justify.

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
and requirement traceability, including PROV-O, OWL-Time, and SHACL.
