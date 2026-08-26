# ADR 0206: Evidence-grounded operations dashboard

- Status: Accepted
- Date: 2026-08-25
- Figma file ID: `1Su3lDRmiZdcUs47t1QwIX`

## Context

The authenticated workspace opens on the Board, so a reader must search and
open records one at a time to assess delayed claim investigation, rebid or
handover gaps, external-market coverage, and a project's changing journey.
The stored corpus already separates source fields from semantic evidence:
`source_post`, `post_project_mention`, `post_summary_event`,
`post_summary_action`, `post_summary_role`, and `post_lineage_edge`.

Those tables do not yet contain claim-case, rebid/handover, specification
change, originating-order, or external-information semantic classifications.
Keyword matching, title fragments, and fixed confidence thresholds cannot
provide them: the same words occur in unrelated operational contexts. The
repository's existing contextual-orchestrator boundary can make a grounded
semantic classification while preserving the cited source span and model-run
provenance.

## Decision

1. `/` opens an evidence-operations Dashboard after authentication. Board
   remains independently reachable from the global navigation.
2. Dashboard requests are bounded by an inclusive event-time period.
   `source_post.event_occurred_at` is the primary clock and `created_at` is the
   explicit fallback, matching ADR 0202. The response names that clock.
3. Every count is authorization-filtered before aggregation. Event count is
   the number of persisted `post_summary_event` rows for the classified,
   visible posts; post count is the distinct count of those posts. Neither
   substitutes for the other, and no event is invented when a summary event
   row is absent.
   Analysis-pending and ingestion-failed post counts are disjoint: a failed
   current job is shown as retryable failure, never hidden inside the pending
   count or interpreted as a negative classification.
4. Extend the existing post-summary semantic workflow through
   contextual-orchestrator with a schema-validated case analysis. It classifies
   zero or more case kinds (`claim_investigation`, `rebid_handover`,
   `external_information`, `repeat_issue`) and extracts the question-specific
   facts. Every positive classification carries a verbatim source evidence span. Keywords,
   regexes, provider-name ordering, local model selection, and hand-authored
   scoring weights are prohibited.
5. Persist the result in normalized post case-analysis tables with the source
   body digest and orchestrator session/run provenance. A changed source body
   invalidates the old result and queues re-analysis through the existing
   content-ingestion lifecycle. Schema-invalid or unavailable results fail the
   job and remain retryable; they are not converted into a negative case.
6. External-information coverage is the distinct count of visible posts with
   a persisted positive `external_information` classification divided by all
   visible posts in the same period. The stored `vom` source code is supplied
   to the orchestrator as labeled evidence, but does not replace semantic
   analysis. Zero total posts yields `0`.
   The external destination passes an API scope so non-external counts and
   case rows are excluded at the SQL boundary, not merely hidden in the UI.
7. Qualitative rows project only persisted evidence:
   project names and evidence spans, source sales-pool code/name, summary
   events, requester/processor action evidence, roles, and Event Lineage links.
   When the focal post lacks an answer, the orchestrator follows authorized
   Event Lineage and semantic project evidence before concluding the fact is
   absent from the authorized corpus.
   The analysis input reuses the post-chat source assembler: focal post first,
   then bounded Event Lineage and semantic-neighborhood posts after the same
   corporate-entity/process-unit ABAC check. Every classification and fact
   persists its evidence post id and the SHA-256 of the exact numbered input
   document. A span that does not occur in that identified document rejects
   the whole provider response; linked evidence is never rewritten as focal
   post evidence.
8. Claim-investigation and rebid/handover panels include positively classified
   cases and show extracted answers plus cited spans. A required answer that
   the source does not support is stored in the normalized
   `operations_case_missing_fact` relation as an explicit missing fact, so the
   next action is collection or human correction rather than keyword guessing.
   A provider result is invalid unless every required question is represented
   exactly once as either a cited supported fact or an explicit missing fact;
   a fact cannot be both. Missing facts carry no invented value or evidence
   span and inherit the analysis run and authorized-source boundary through
   their classification parent.
9. Project membership uses only an explicit source project or stored semantic
   project mention. A multi-project post may appear in multiple groups;
   unbound events remain unassigned. A chronological sort of those records is
   only a **project-observed-event list**, not a Project Journey. Project
   Journey starts, predecessors, branches, and transitions consume a
   provenance-bearing TEPP TDT/CHRONOS result. Previous projects, customer
   requests, procurement notices, negotiated/direct bidding, external
   sensing, internal discussions, and sales leads are all admissible starts or
   predecessors when the accepted TEPP artifact and source evidence connect
   them. LineageWeave never chooses a fixed first stage or promotes nearest-date
   ordering to a lineage edge.
10. A repeat-issue result carries both the issue-pattern evidence and any
   source-supported improvement action. Its Dashboard flow is As-Is evidence
   to To-Be action: rebid history retrieval, originating-order/specification
   reverse tracing, repeated-issue grouping, and design-improvement return.
   Similarity alone never establishes that two issues are the same type. The
   per-post Similar VOC view uses visible `repeat_issue` classifications only
   as a semantic candidate pool, then requires contextual-orchestrator to
   adjudicate each pair with verbatim evidence from both records. Results are
   displayed by source event time, not a similarity score. It does not reuse
   Event Lineage channel weights, and it does not invoke RankWeave without a
   separately authorized Similar-VOC measurement contract. Candidate
   adjudication is paged in eight-record resource batches with an explicit
   continuation offset; the page boundary caps request fan-out but does not
   discard older candidates or become a relevance threshold.
11. The Dashboard uses existing design tokens and native HTML controls. Tables
   and ordered journey steps remain usable without color, with visible focus,
   keyboard activation, responsive overflow, and reduced-motion support.
12. Storybook records populated, empty, analysis-failed, missing-evidence,
   error, desktop, and narrow-viewport scenes. Runtime screenshot review uses
   synthetic data only.
13. The Dashboard does not add a separate external-information Board. Its GNB
   destination contains the external count/rate and evidence filter; opening a
   result reuses the existing Board post detail.
14. TEPP is the measurement authority. Similar-VOC quality and operational
   outcome measures consume only accepted and persisted TEPP results. The
   Dashboard never creates a local theta or repairs a missing TEPP envelope.
   The current fast-mlsirm Event Lineage experiment is unanchored and inactive
   under ADR 0145/0200; the Dashboard does not consume its candidate vectors.
   RankWeave may fuse channels only after an independently anchored vector is
   authorized, and that rank is never a psychometric measure or substitute for
   TEPP. Missing estimates remain unavailable; no hand-picked weight is
   introduced.
15. Operations classifications and facts have a governed OWL/JSON-LD read
   projection. Each case is a `prov:Entity`; each fact is an RDF-reified
   `prov:Entity` linked to its exact cited Post by `prov:wasDerivedFrom`.
   External-information relations carry a provider-returned, closed semantic
   target type (`order`, `project`, `sales`, or `business_management`) and map
   to typed ontology properties. This is not a `knowledge_graph_edge` alias:
   PostgreSQL operations tables remain authoritative, and an older untyped
   relation remains absent from the typed projection until re-analysis.
16. Claim investigation and rebid/handover use an observed event-log contract
   aligned with IEEE 1849-2023 (XES). A classification is the local analysis
   case identifier; a milestone has a closed activity code, an exact cited
   evidence span, its evidence post, source digest, observed instant, and named
   clock. Cross-post business-case identity is not inferred from project,
   similarity, proximity, or text.
17. Claim investigation pairs `claim_received` with `cause_confirmed`.
   Rebid/handover independently pairs `rebid_response_requested` with
   `rebid_decision_recorded`, and `handover_started` with
   `handover_accepted`. The database rejects a claim milestone on a
   rebid/handover case, a rebid/handover milestone on a claim case, and every
   milestone on the other case kinds; the same invariant applies to observed
   and explicitly missing endpoints. Contextual-orchestrator identifies the supported
   milestone semantics; LineageWeave assigns the instant only from that cited
   `source_post`: `event_occurred_at` when present, otherwise the explicitly
   labeled `created_at` fallback from ADR 0202. The model never emits a date.
18. Each required endpoint is exactly one cited milestone or one normalized
   missing-milestone row. Both observed endpoints produce the exact duration
   `end - start`; start plus an explicitly missing end is `open`; a missing
   start is `evidence_missing`. An open case has no elapsed duration because
   no end instant was observed. Reversed observed endpoints reject the entire
   provider result. No delay threshold, severity band, current-time endpoint,
   imputed date, average, score, or arbitrary weight is introduced. Equal
   source instants yield an auditable zero duration; they are not replaced by
   an invented sub-record timestamp.
19. The API rechecks the reader's current ABAC and source eligibility for each
   classification, fact, and milestone evidence post before returning its
   span. Consequently, aggregate counts exclude classifications whose cited
   evidence is no longer authorized. The UI reports open, resolved, and
   evidence-missing counts separately, shows exact elapsed seconds in a
   lossless human-readable form, names each milestone's clock, and links the
   reader to both endpoint sources. State and next action are conveyed in text
   rather than color alone.

## Consequences

The landing page answers what is known, how much evidence exists, and which
field or relationship must be obtained next. Classification is inferred inside
the governed stack and remains auditable through source spans and run
provenance; operational failure is visible and retryable rather than silently
treated as a negative case.

## Verification

- Parser and persistence tests cover multi-label output, cited spans, malformed
  responses, source-digest invalidation, and unavailable orchestrator states.
- Backend integration tests cover ABAC filtering, event-time fallback, event
  versus post counts, external-information percentage, multi-project
  membership, explicit missing facts, observed lifecycle endpoints, exact
  elapsed duration, open cases with nullable elapsed time, reversed endpoint
  rejection, and evidence-post authorization.
- Frontend tests cover period submission, navigation, empty/error states,
  evidence links, keyboard semantics, and non-color status copy.
- Storybook interaction tests and authenticated browser screenshots audit the
  rendered desktop and narrow layouts.

## References

Institute of Electrical and Electronics Engineers. (2023). *IEEE standard for
eXtensible Event Stream (XES) for achieving interoperability in event logs and
event streams* (IEEE Std 1849-2023). IEEE Standards Association.
https://standards.ieee.org/ieee/1849/10907/

van der Aalst, W. M. P., Adriansyah, A., de Medeiros, A. K. A., Arcieri, F.,
Baier, T., Blickle, T., Bose, J. C., van den Brand, P., Brandtjen, R., Buijs,
J., Burattin, A., Carmona, J., Castellanos, M., Claes, J., Cook, J., Costantini,
N., Curbera, F., Damiani, E., de Leoni, M., ... Wynn, M. (2012). Process mining
manifesto. In F. Daniel, K. Barkaoui, & S. Dustdar (Eds.), *Business process
management workshops* (pp. 169–194). Springer.
https://doi.org/10.1007/978-3-642-28108-2_19

World Wide Web Consortium. (2022). *Time ontology in OWL*.
https://www.w3.org/TR/owl-time/
