# ADR 0052: Plain contextual-orchestrator semantic evidence contract

- Status: Accepted
- Date: 2026-08-19

## Context

The post-summary channel must produce both a readable 5W1H summary and the
semantic projections used for Ontology, Keyman, project, and customer
navigation. The nested JSON response contract was unreliable with the local
contextual-orchestrator route: responses could contain reasoning without a
complete content object. Returning only the plain summary made the UI look
healthy while silently discarding roles and project mentions.

## Decision

`ContextualOrchestratorPostSummaryClient` makes two sequential calls to
contextual-orchestrator, both with `mode=route` and no raw LLM or provider call:

1. The first call returns a Korean evidence-grounded summary followed by a
   `KEY EVENTS:` line.
2. The second call returns `ROLES:` and `PROJECTS:` sections. Each role row is
   `actor | responsibility | actor type | affiliation`; a compact three-field
   role row defaults to the existing `prov_person` contract. Each project row
   is `name | canonical name | evidence | confidence`; a compact three-field
   row is `name | evidence | confidence` and derives only the deterministic
   comparison key with `normalize_project_key`.

Structured source fields remain weak, provenance-labelled hints. Values such
as `기타`, `미등록고객`, `unknown`, and `other` cannot confirm a customer or
project. A project row with `NONE` evidence is discarded. The only permitted
fallback is the source post title when the extracted project name is an exact
case-insensitive substring of that title; the title is then the stored
evidence, not an invented sentence.

The resulting `RoleResponsibility` and `ProjectMention` objects continue
through the existing catalog/provenance persistence path. A malformed
semantic response is an unavailable summary channel; the source body remains
visible and no empty semantic result is presented as successful extraction.
The persisted summary contract version is bumped so summaries written before
this two-call semantic contract are regenerated instead of being served as
current evidence. The Buyer UI renders the localized ontology label and
localized extraction/provenance labels; it never renders the ontology IRI or
contextual-orchestrator/storage identifiers as user-facing text.

Ask Agent citations expose the persisted source and semantic facts associated
with each cited post through a Buyer-safe projection. Prompt metadata such as
ontology IRIs, provider names, extraction identifiers, and storage provenance
is removed from that projection; the cited post remains the authoritative path
for reading the complete body and related evidence.

## Consequences

- Semantic roles and projects are no longer silently dropped when the summary
  call succeeds.
- The channel incurs a second orchestrator request and therefore a bounded
  latency/cost increase.
- Plain line parsing is intentionally narrow; unsupported provider output is
  rejected rather than promoted into ontology facts.

## Verification

- Unit tests cover both plain calls, compact rows, title-backed evidence, and
  rejection of unsupported project evidence.
- Runtime verification uses only the repository's synthetic fixture and the
  contextual-orchestrator service.
