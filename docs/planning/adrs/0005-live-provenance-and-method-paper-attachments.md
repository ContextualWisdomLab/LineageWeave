---
id: "0005"
title: "Persist live LLM provenance and original method-paper attachments"
status: accepted
proposed_date: 2026-08-14
accepted_date: 2026-08-14
deciders:
  - "LineageWeave delivery owner"
consulted:
  - "TEPP evidence and orchestration contract"
  - "Zotero Connector local API"
informed:
  - "PostgreSQL, model, and research operators"
related:
  - path: "docs/planning/adrs/0001-lineageweave-runtime-and-governance.md"
    relation: "influenced-by"
    note: "Keeps source bytes and external research artifacts outside graph JSON."
  - path: "docs/planning/adrs/0004-evidence-verified-ontology-inference.md"
    relation: "influenced-by"
    note: "Applies the same durable provenance rule to LLM-derived Keyman and research artifacts."
affected_components:
  - "lineageweave.py"
  - "sql/"
  - "tests/test_lineage_runtime_contract.py"
  - "notes/lineageweave_milestone2_run_summary.md"
success_criteria:
  - metric: "Keyman provenance"
    target: "LLM-derived and user-overridden two-sided Keyman values remain distinguishable after reload."
    measurement_window: "each persisted document reload"
    source: "analysis_document_overrides.keyman_source and keyman_status"
  - metric: "Research artifact provenance"
    target: "Each configured method-paper parent and bounded original attachment records its Zotero outcome and SHA-256."
    measurement_window: "each method-paper storage run"
    source: "analysis_method_paper_records"
  - metric: "Bounded transfer"
    target: "An original attachment larger than 32 MiB is rejected before it reaches Zotero."
    measurement_window: "each attachment request"
    source: "MAX_METHOD_PAPER_ATTACHMENT_BYTES and contract tests"
effort: S
---

# ADR-0005: Persist live provenance and original method-paper attachments

## Context

The product has two provenance-sensitive write paths. A live LLM can derive a
two-sided Keyman, while a user can subsequently curate it. A metadata-only
research record does not prove that the cited OA source was retained, and a
successful Zotero parent write does not prove that its original attachment was
stored. Treating either distinction as an in-memory detail makes restart and
audit behavior ambiguous.

> Citation: Zotero. (2026). *Zotero Web API v3: File uploads*.
> https://www.zotero.org/support/dev/web_api/v3/file_upload

> Citation: World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*.
> https://www.w3.org/TR/prov-o/

> Citation: ContextualWisdomLab. (2026). *TEPP: Evidence, provenance, and
> adaptive orchestration contracts*. https://github.com/ContextualWisdomLab/TEPP

## Decision Drivers

- Preserve model and user provenance through restart.
- Retain the original research artifact only through an explicit bounded
  Connector contract.
- Keep source bytes and external research metadata outside the KG payload.
- Make attachment failure visible rather than labeling a citation as stored.

## Considered Options

| Option | Provenance | Transfer safety | Decision |
| --- | --- | --- | --- |
| Store only a paper title in process memory | Lost on restart | No attachment boundary | Rejected |
| Store source bytes in the graph JSON | Ambiguous ownership and evidence scope | Inflates graph and browser payloads | Rejected |
| Use Local Zotero Connector metadata plus bounded original attachment and PostgreSQL status | Restart-safe and auditable | Size, URL, digest, and status checks | Accepted |

## Decision

| Driver | Selected boundary | Result |
| --- | --- | --- |
| Provenance | PostgreSQL status plus exact Zotero parent/child verification | Restart-safe audit |
| Transfer safety | Bounded HTTPS OA download and Connector attachment contract | Oversize and failed writes remain visible |
| Payload separation | Research artifacts stay outside graph JSON | KG remains bounded |

Persist `keyman_source` and `keyman_status` on document overrides. The LLM
adapter writes `llm`/`orchestrator`; an explicit user mutation writes
`user_override`/`managed`. Existing rows receive the conservative user-origin
default during additive migration.

When `LINEAGEWEAVE_ZOTERO_ATTACHMENTS=1`, the Local Zotero Connector receives
the method-paper parent through `saveItems`, then the bounded public original
through `saveAttachment` using the Connector's `sessionID` query and
`X-Metadata` session/parent contract. The PostgreSQL record stores parent status,
attachment status, optional attachment key, and the downloaded bytes' SHA-256.
The feature remains opt-in so metadata-only tests and deployments that do not
permit external retrieval remain honest; a run never labels a failed
attachment as stored.

Before creating another parent, a repeat run reads the bounded local Zotero
inventory and reuses only an exact title plus source-URL match. With attachment
storage enabled, reuse is accepted only when a child attachment has the same
source URL and the freshly downloaded bytes reproduce its recorded SHA-256.
Historical duplicates are audit records and are not deleted by this product.

The source remains external to graph JSON. The Zotero record is a research
provenance artifact, not an authorization bypass or a substitute for source
evidence.

## Consequences

- Restarted API reads preserve whether Keyman came from the live LLM or a user.
- Research operators can distinguish a stored original from a stored citation.
- Attachment retrieval is bounded, TLS-verified, and limited to configured HTTP(S)
  OA sources; failures remain visible as `unreachable` or `rejected`.
- The product does not infer that a Zotero write validates a paper's claims.
- Repeated analysis is idempotent for an exact paper/attachment pair; ambiguous
  or digest-mismatched records are not silently treated as the requested item.

## Affected Components

- `lineageweave.py` owns the Connector adapter and PostgreSQL provenance rows.
- `analysis_method_paper_records` stores status, keys, and content digest.
- `tests/test_lineage_runtime_contract.py` covers connector success and failure.
- `notes/lineageweave_milestone2_run_summary.md` records aggregate runtime evidence.

## Risks and Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| Public source is unavailable | Persist `unreachable` and keep the metadata outcome explicit | attachment outage contract |
| Connector returns a misleading key | Re-read the exact parent/child and verify URL and digest | repeat-run contract |
| Large bytes exhaust the process | Enforce bounded read before Connector upload | oversized attachment contract |
| Research metadata is treated as source truth | Keep it outside the KG and label it provenance only | architecture and source-boundary tests |

## Rollback / Exit Strategy

Disable `LINEAGEWEAVE_ZOTERO_ATTACHMENTS` to stop original retrieval while
retaining the method-paper metadata rows. If the feature is retired, preserve
the PostgreSQL provenance table for audit, stop Connector writes, and remove
only the optional attachment worker path after an operator backup. Do not delete
historical research records as part of product rollback.

## Verification

- Unit and integration contracts cover parent-only, attachment success, source
  outage, HTTP rejection, oversized, empty, and malformed-connector responses.
- `analysis_method_paper_records` is checked after a live Local Zotero run for
  thirteen stored parents, thirteen stored attachments, and thirteen non-empty
  digests, including LayoutLM, LayoutLMv2, DocFormer, Donut, and RAGAS.
- A connector contract test proves that an exact parent and child attachment
  are reused without issuing another write and that the content digest is
  recomputed from the OA source.

## References

Zotero. (2026). *Zotero Web API v3: File uploads*. https://www.zotero.org/support/dev/web_api/v3/file_upload

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology*. https://www.w3.org/TR/prov-o/

ContextualWisdomLab. (2026). *TEPP: Evidence, provenance, and adaptive orchestration contracts*. https://github.com/ContextualWisdomLab/TEPP

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management. *IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44. https://homes.cs.aau.dk/~csj/Papers/Files/1999_jensenIEEETKDE.pdf

Swanson, M., Bowen, P., Phillips, A. W., Gallup, D., & Lynes, D. (2010). *Contingency planning guide for federal information systems* (NIST Special Publication 800-34 Rev. 1). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-34r1
