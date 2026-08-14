---
id: "0002"
title: "Inspect bounded inline images through verified model trust"
status: accepted
proposed_date: 2026-08-13
accepted_date: 2026-08-13
deciders:
  - "LineageWeave delivery owner"
consulted:
  - "product request"
informed:
  - "Keyverse, database, and model-gateway operators"
related:
  - path: "docs/planning/adrs/0001-lineageweave-runtime-and-governance.md"
    relation: "influenced-by"
    note: "Extends the direct PostgreSQL and Keyverse boundary with bounded image inspection."
affected_components:
  - "lineageweave.py"
  - "lineageweave_server.py"
  - "web/src/App.jsx"
  - "compose/http_standin.py"
  - "analysis_content_inspections"
  - "analysis_content_inspection_labels"
  - "analysis_object_label_catalog"
asr_triggers:
  - kind: security
    evidence: "Untrusted inline image bytes cross a model boundary only after authorization and validation."
    note: "The request needs strict MIME, base64, signature, and TLS checks."
  - kind: performance
    evidence: "The source contains multi-megabyte inline images and cells larger than 40 MB."
    note: "Only bounded raster assets can enter OCR; graph and search stay metadata-only."
  - kind: compliance
    evidence: "OCR and labels remain source-derived, actor-attributed, and document-scoped."
    note: "No raw image bytes or private digests are placed in default API or graph responses."
  - kind: availability
    evidence: "A private gateway certificate must not force an insecure TLS bypass."
    note: "Platform trust or an explicitly mounted CA bundle keeps calls verified."
  - kind: maintainability
    evidence: "Object descriptions vary by image even when labels share a name."
    note: "Descriptions belong on the inspection-label relation, not the global label catalog."
success_criteria:
  - metric: "source image discovery"
    target: "Classify a data URI or SVG marker wherever it occurs in the source cell without selecting source bytes into the snapshot."
    measurement_window: "each source snapshot"
    source: "build_source_query content_has_inline_image"
  - metric: "inline-image validation"
    target: "Reject unsupported, malformed, signature-mismatched, or over-limit assets before the model call."
    measurement_window: "each inspection request"
    source: "prepare_content_inspection_asset"
  - metric: "persistence normal form"
    target: "Keep labels in a catalog and image-specific descriptions in the inspection-label relation."
    measurement_window: "each persisted inspection"
    source: "analysis_content_inspection_labels"
  - metric: "transport trust"
    target: "Use hostname-verifying HTTPS with platform trust or an operator CA bundle; no insecure context exists."
    measurement_window: "each live model request"
    source: "verified_gateway_ssl_context"
  - metric: "authorization and search scope"
    target: "Only authorized writers can inspect and only visible documents can appear in OCR search."
    measurement_window: "each API request"
    source: "authorize_access and image_search"
effort: M
---

# ADR-0002: Inspect bounded inline images through verified model trust

## Context

> Product requirement: a large source cell can be an inline image, so byte size alone must not treat it as prose.

> ADR-0001 requires direct PostgreSQL source access, server-side Keyverse authorization, and no raw content bytes in the graph payload.

> Direct source audit on 2026-08-13 found 7,084 rows containing inline image data; 6,955 met the 6 MiB inspection ceiling, 129 exceeded it, and the largest content cell was 49,648,256 bytes.

Inline data in a text column is evidence, not a signal to export the full cell to the browser or graph. The earlier metadata-only boundary correctly prevented unbounded serialization but did not define an executable OCR/object-inspection path or a normalized way to persist its results. A large field can be a raster image, markup, or opaque binary data; only the first category can safely participate in the selected vision contract.

The short prefix is intentionally insufficient as a classifier: a valid inline
image marker can occur later in a large cell. The source projection therefore
computes `content_has_inline_image` inside PostgreSQL while returning only that
boolean, byte length, and bounded prefix to the snapshot.

An image is also untrusted input. It can contain misleading instructions, malicious base64, a type mismatch, or sensitive content. The model request must therefore be bounded, authorized, verified over HTTPS, and devoid of unnecessary document body or internal identifiers. The result must remain tied to the exact image digest and source evidence so a changed asset cannot reuse stale OCR.

## Decision Drivers

- Preserve direct PostgreSQL as the source of truth and keep source bytes out of the persisted KG and default APIs.
- Make inspection useful through controlled OCR/object search without widening tenant visibility.
- Retain TLS verification even when a deployment uses a private certificate authority.
- Keep object labels and image-specific descriptions in third normal form.
- Give operators a recoverable path when the model gateway or Valkey is unavailable.

## Considered Options

| Option | Security and authorization | Data integrity | Operational behavior | Decision |
| --- | --- | --- | --- | --- |
| Serialize data URIs into graph JSON and inspect in the browser | Exposes bytes and bypasses server controls | Cannot reliably bind results to current source evidence | Large payloads and browser memory risk | Rejected |
| Store OCR and descriptions as JSON or mutable global label text | Smaller initial change | Duplicate labels overwrite image-specific meaning | Hard to query and audit precisely | Rejected |
| Direct source retrieval with bounded server-side inspection, normalized relations, and verified HTTPS | Uses existing Keyverse and document authorization | Digest-bound results and relation-scoped descriptions | Fails closed or leaves durable events pending | Accepted |

## Decision Outcome

Adopt an on-demand, document-scoped image-inspection flow. The server retrieves an inline asset directly from PostgreSQL only after it verifies document visibility and the author/editor/admin inspection permission. It accepts only PNG, JPEG, GIF, or WebP data URIs with strict base64 decoding, matching magic bytes, and a decoded size at or below 6 MiB. SVG, EMF, opaque binary data, malformed payloads, and larger assets remain authorized for retrieval but are not sent to the vision model.

| Decision driver | Selected implementation |
| --- | --- |
| Source and byte boundary | Compute an inline-image/markup marker inside the bounded runtime projection, build a document-local asset index directly from the runtime table, return metadata by default, and return image bytes only through the existing authorized asset route. |
| Model trust | Prefer direct live HTTP; create a hostname-verifying context from the platform trust store or `LLM_GATEWAY_CA_BUNDLE`. Never disable certificate validation. |
| Prompt-injection boundary | Send only the validated image and minimal task shape; the system instruction treats rendered content as untrusted data. |
| Result identity | Persist source evidence, source row, asset position, MIME type, SHA-256 digest, model, actor, and timestamp. Display results only when the current asset digest matches. |
| Relational design | Store unique label names in `analysis_object_label_catalog`; store label position and image-specific description in `analysis_content_inspection_labels`; keep OCR on `analysis_content_inspections`. |
| Search and events | Search OCR and label relations only for documents visible to the current actor. Record a metadata-only `content_inspected` outbox event for Valkey delivery. |

The global label catalog intentionally has no description column. A label such as `diagram` can describe different things in two images; its explanation is dependent on the specific inspection-label relationship, not on the label name. The migration copies any prior catalog description to existing relationships before removing the mutable global description.

## Consequences

Positive:

- The product can inspect a real inline source image without leaking its bytes into the KG, default document response, or image search result.
- The marker detects an inline image or SVG that begins after the short prefix,
  so a large cell is not silently misclassified as ordinary prose.
- OCR and object labels are queryable through normalized tables while retaining source evidence and the inspecting account.
- A changed inline image invalidates old UI output by digest mismatch rather than silently showing stale OCR.
- TLS stays verified on macOS through the platform trust store and can use a deployment-mounted CA bundle.

Trade-offs:

- Users must request inspection and need a write-capable Keyverse role; readers can only view matched, authorized metadata.
- The 6 MiB and raster-only policy intentionally leaves some images uninspected. The original authorized asset route still serves those assets.
- Model output is not source truth. It is labeled with the model and stays separate from observed lineage transitions.
- Valkey publication is at-least-once, so consumers must continue to deduplicate the metadata-only event ID.

## Risks and Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| Image payload contains malicious instructions | Validate bytes before use and direct the model to treat image content as untrusted data | `prepare_content_inspection_asset`, live request shape |
| Wrong asset receives an old OCR result | Use a document-local index plus SHA-256 matching before rendering an inspection | `_document_assets`, `content_manifest` |
| Inline marker occurs beyond the short prefix | Compute a `content_has_inline_image` marker in PostgreSQL while retaining only bounded metadata in the snapshot | `build_source_query`, runtime marker test |
| A private CA tempts an insecure bypass | Use platform trust or a configured CA bundle and fail closed on certificate failure | `verified_gateway_ssl_context` |
| Cross-tenant OCR search leak | Derive the visible document set before the parameterized PostgreSQL search | `image_search`, `filter_payload_for_actor` |
| Label description is overwritten by another image | Keep it on the inspection-label relation rather than the global catalog | `persist_content_inspection` and relation test |
| Gateway or Valkey is unavailable | Return a bounded worker failure; retain committed inspection event in the PostgreSQL outbox for later delivery | `analysis_event_outbox`, queue health |

## Rollback / Exit Strategy

1. Disable the inspection route or remove its writer permission without deleting source images or historical inspection records.
2. Stop the worker or remove its gateway configuration; existing metadata remains auditable and no insecure transport fallback is enabled.
3. If a schema rollback is required, retain the three inspection tables read-only and restore the prior application version. Do not recreate a mutable global description column from image-specific descriptions.
4. Drain or replay pending `content_inspected` outbox events using `event_id` before changing Valkey consumers.
5. Re-run the inspection only after the source image and model-trust configuration have been verified.

## Affected Components

- `lineageweave.py`: strict inline-raster validation, verified gateway context, normalized persistence, and migration.
- `lineageweave_server.py`: document-local asset indexing, authorization, digest matching, image search, and outbox event creation.
- `web/src/App.jsx`: inspection control, OCR/object display, and scoped image-search navigation.
- `compose/http_standin.py` and `compose.yaml`: live model proxy and optional CA bundle only; no identity authority.
- PostgreSQL tables `analysis_content_inspections`, `analysis_content_inspection_labels`, and `analysis_object_label_catalog`.
- `tests/test_prototype_surfaces.py`: transport, persistence, role, React route, and per-relation description checks.

## Verification and Monitoring

- Full local tests cover strict image validation, verified TLS request shape, normalized persistence, description isolation, role enforcement, and React routes.
- The source-query contract and runtime test verify that a large cell with a
  late inline-image marker is classified without exporting the cell bytes.
- On 2026-08-14, controlled operator-triggered direct-PostgreSQL runs completed seven live HTTPS model inspections across three documents. Every persisted inspection has non-empty OCR and model fields, and none contains the rejected placeholder marker. Six current asset profiles across two materialized documents remain inspection-eligible; the seventh inspection is retained as historical digest-bound evidence. The record is aggregate-only: no source bytes, identifiers, digest, OCR text, or labels are included here.
- Operators can inspect `/api/queue/health` for Valkey readiness and pending outbox records. Model tokens, source bytes, and image digests are never emitted by that endpoint.

## Amendment: Large inline-image eligibility (2026-08-15)

The former 6 MiB decoded-image ceiling was too narrow for the observed source:
the largest source cell is 49,648,256 bytes and a cell above 40 MB can still be
an inline raster image rather than prose or a separate attachment. The current
ceiling is therefore 50 MiB. It remains an inspection-request boundary only;
raw bytes are still absent from the graph, default API responses, browser
payload, embeddings, and Valkey events.

`inspection_eligible` is now recalculated from persisted MIME and encoded-size
metadata when a document structure is read. This allows structures materialized
under the former ceiling to expose an authorized inspection action without
copying the data URI or rewriting the source row. Strict raster MIME, base64,
magic-byte, authorization, digest, TLS, normalized persistence, and outbox
requirements are unchanged.

The change does not claim that an external model gateway accepts every 50 MiB
request. A real configured gateway must still prove that acceptance; an HTTP
rejection remains an explicit failed inspection and never becomes a placeholder
or a fabricated OCR result. Assets above the 50 MiB cap remain available through
the authorized asset route and are not serialized into product graph data.

Verification for this amendment is a metadata-only regression: a persisted
40 MiB encoded image record that was marked ineligible under the old policy is
re-evaluated as eligible, while oversized, non-raster, and malformed size
metadata remain ineligible. No additional live image inspection was run.

## References

ContextualWisdomLab. (2026). *TEPP research and evidence notes*. Local repository material summarized in `notes/tepp_research_notes.md`.

LineageWeave. (2026). *ADR-0001: Run LineageWeave as a direct-PostgreSQL governed product*. `docs/planning/adrs/0001-lineageweave-runtime-and-governance.md`.

LineageWeave. (2026). *Direct PostgreSQL inline-image audit*. Runtime query performed on 2026-08-13; aggregate counts recorded in this ADR.
