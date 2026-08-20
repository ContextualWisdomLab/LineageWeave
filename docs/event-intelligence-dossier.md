# Event Intelligence Dossier v1

## Buyer outcome

The dossier answers a single operational question without hiding scientific
boundaries:

> What event is being asserted, what did the system know at the requested
> cutoff, which entities and relations make it relevant, what did TEPP and
> fast-mlsirm measure, what did the LLM judge conclude, and exactly which
> evidence supports every claim?

It is designed for an Event Intelligence detail surface, export, API response,
or MCP context bundle. It is not a second event database and not a new blended
score.

## Product composition

```text
Immutable source evidence + clocks
              |
              v
LineageWeave knowledge graph + ontology
              |
              +-----------> TEPP temporal/topic artifact
              |
              +-----------> fast-mlsirm calibrated artifact
              |
              +-----------> contextual-orchestrator verdict
              |
              v
Event Intelligence Dossier v1
              |
              +-- buyer claims with evidence IDs
              +-- canonical SHA-256
              +-- JSON Schema / CLI validation
```

Each provider keeps its own authority. The dossier only verifies that the
artifacts belong to the same snapshot/cutoff and that every surfaced claim,
node, edge, and measurement resolves to committed evidence.

## Required and optional channels

| Channel | Required | Failure representation |
|---|---:|---|
| Temporal context | yes | dossier rejected |
| Ontology references | yes | dossier rejected |
| Immutable evidence | yes | dossier rejected |
| LineageWeave knowledge graph | yes | dossier rejected |
| TEPP | no | `status_code=unavailable` |
| fast-mlsirm | no | `status_code=unavailable` |
| contextual-orchestrator | no | `status_code=unavailable` |
| Grounded claims | may be empty | empty array |

An unavailable channel is different from an estimated value of zero.

## Temporal model

The contract retains:

- `event_start` and optional `event_end`;
- `assertion_time`;
- `document_time`;
- `available_time`;
- `knowledge_cutoff`.

A document written later may legitimately describe an earlier event. It may
only enter an analysis whose cutoff is at or after the document became
available. This prevents retrospective reports from becoming future
information in historical runs.

## Relevance and uncertainty

A `RelevanceMeasurement` always states:

- method code and method version;
- authority system;
- estimate;
- lower and upper uncertainty bounds;
- evidence IDs.

LineageWeave graph relevance, TEPP topic relevance, and fast-mlsirm calibrated
measurement are not treated as the same scale. The orchestrator channel has no
`estimate` or `psychometric_score` field.


## Contextual-orchestrator judgment boundary

The lineage pair-adjudication client no longer asks for a bare number and no
longer searches arbitrary prose with a regular expression. It sends candidate
labels as a canonical JSON data object under a system instruction that marks
them untrusted, requests `mode=verify`, high reasoning effort, and an
orchestration trace, then accepts exactly these fields:

```json
{
  "continuation_probability": 0.74,
  "verdict_code": "supported",
  "rationale": "The second record continues the same operational action."
}
```

Code fences, extra or missing fields, duplicate keys, non-finite values, and
out-of-range probabilities fail closed. The compatibility `judge()` method
returns only the validated probability; `judge_decision()` exposes the full
structured decision for dossier composition.

## Validate an artifact

After installing the package:

```bash
lineageweave-validate-event-intelligence \
  examples/event-intelligence-dossier-v1.json
```

Successful output is a compact machine-readable receipt:

```json
{"contract_version":1,"dossier_sha256":"...","event_id":"...","status_code":"valid"}
```

Invalid UTF-8, malformed JSON, unknown fields, missing fields, altered digests,
cutoff leakage, dangling graph edges, or unknown evidence references produce a
bounded JSON error on stderr and exit code `2`. Source text and Python
tracebacks are not printed.

## Python composition

```python
from lineageweave.event_intelligence import (
    EventIntelligenceDossier,
    event_intelligence_dossier_from_dict,
)

# Validate an artifact received from an API or object store.
dossier = event_intelligence_dossier_from_dict(payload)
assert isinstance(dossier, EventIntelligenceDossier)

# Emit canonical JSON and a reproducibility digest.
wire_json = dossier.to_json()
digest = dossier.dossier_sha256()
```

The canonical example is
`examples/event-intelligence-dossier-v1.json`; the published schema is
`schemas/event_intelligence_dossier_v1.schema.json`.

## Digest canonicalization

`dossier_sha256` is SHA-256 over the UTF-8 bytes produced by RFC 8785 JSON
Canonicalization Scheme (JCS) after removing the `dossier_sha256` member. JCS
recursively sorts object members, preserves array order, emits no whitespace,
and rejects non-finite numbers; its I-JSON number boundary also prevents an
unsafe integer from becoming a different value in another runtime. `to_json()`
uses the same JCS serialization with the digest member present, so a buyer can
recompute the digest without relying on Python's ordinary JSON formatting.

## Downstream integration contract

A future backend endpoint should:

1. authorize the buyer and the source evidence independently;
2. resolve one immutable source snapshot and knowledge cutoff;
3. materialize the visible LineageWeave graph neighborhood;
4. attach TEPP only after validating its published reproducibility manifest;
5. attach fast-mlsirm only with its scale, model version, uncertainty, and
   digest;
6. request a structured, evidence-bounded orchestrator verdict;
7. compose the dossier and persist or return its digest;
8. render exact values and evidence links in the buyer UI.

The endpoint must not query TEPP or fast-mlsirm application tables directly and
must not let the LLM create source evidence, ontology authority, or numerical
measurement.
