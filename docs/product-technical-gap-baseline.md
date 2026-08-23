# Product & Technical Gap Baseline

## 1. Parsing and reader display

- **Footnotes**: Synthetic markerless, HTML, Word, citation, and OOXML cases are covered on active PR #446. Authorized runtime validation remains aggregate and non-identifying.
- **Tables**: Partially resolved. Synthetic DOM tests prove row-atomic parsing and malformed inline-script isolation on PRs #447 and #427; authenticated reader rendering remains open.
- **Indentation**: Source indentation is preserved for orchestrator adjudication on PR #394. Hosted frontend CI is being rerun after a transient Corepack download failure.
- **Image/table understanding**: Region evidence and reader rendering exist on PRs #405 and #419. Authenticated table-in-image OCR quality remains open.
- **Math and superscripts**: Plain caret and HTML `sup`/`sub` quantities are normalized on PR #427; general mathematical grammar remains open.
- **Lineage DAG**: The reader DAG and Storybook coverage exist on stacked PR #438, based on terminology PR #474.

## 2. Semantic and knowledge-graph evidence

- **Multiple projects, 5W1H, roles, and Keyman**: Synthetic extraction and persisted evidence paths exist. Co-occurrence is not promoted to project, responsibility, or affiliation evidence.
- **Entity resolution**: Ambiguous organization names remain unbound; live search hints are corroborating evidence only. Authenticated runtime verification remains open.
- **Omni-modal evidence**: Image regions, OCR, captions, and embeddings cross `contextual-orchestrator`; unsupported or incomplete evidence stays unavailable.

## 3. Internal-library integration

- **ThreadWeave**: Integrated in the production reconstruction path; no local tree-assembly substitute is planned.
- **RankWeave**: Integrated through the in-process ranking port and fails closed when the package is unavailable or disabled.
- **fast-mlsirm**: PR #468 pins the refreshed internal package. GRM, GPCM, CAT, and FIPC recovery evidence is split across PRs #451-#454; item-parameter calibration claims remain open where those tests measure theta recovery only.
- **Keyverse**: PR #468 binds `org`, `workspace`, and roles to one provisioned organization/process-unit affiliation under ADR 0156. The strict contract intentionally denies incomplete affiliations.
- **contextual-orchestrator**: PR #468 routes generative, VISION, structured-output, and embedding work through the provider-neutral boundary. Upstream model discovery and paper-grounded selection remain contextual-orchestrator responsibilities, not LineageWeave heuristics.
- **TEPP**: PR #468 sends the published analysis-run body with LineageWeave consumer, contract-version, and idempotency headers and removes the rejected credential-header option. Provider PR TEPP #155 must merge and be deployed before requests can be accepted; completed-result contract/persistence remains dependent on TEPP #157. No local theta substitute is allowed.
- **Other organization repositories**: `disksage` and `wardnet` do not satisfy a demonstrated LineageWeave product boundary, so no dependency is added.

## 4. Remaining architecture and governance gaps

- **PostgreSQL**: Production persistence uses PostgreSQL and normalized provenance tables. Hot-partition and read-replica work requires measured load evidence before implementation.
- **Research references**: APA 7 references are maintained in ADRs and research notes. Local Zotero synchronization remains an operator tooling gap, not runtime authority.
- **Security and compliance**: PII controls must preserve authorized evidence and provenance. SOC 2 and CSAP evidence mapping remains open.
- **Protected delivery**: Review threads are resolved at the latest audit snapshot, but open PRs remain blocked on independent approval and, for recently updated heads, terminal hosted checks. Local success is not merge evidence.

This file records only synthetic or aggregate non-identifying evidence. It is updated as protected-main evidence changes.
