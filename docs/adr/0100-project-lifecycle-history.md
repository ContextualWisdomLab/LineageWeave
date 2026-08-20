# ADR 0100: Evidence-bound project lifecycle history

- Status: Accepted
- Date: 2026-08-20
- Issue: #280
- Figma: `SBpgot7uTvMxEaxUwvoc0S`, node `308:2`

## Context

The Buyer surface can open one source post and inspect its Event Lineage,
project hints, Keymen, tickets, and evidence. It cannot yet read one project's
order, specification change, delivery, VOC, and rebid history on a single
ordered surface. It also cannot distinguish recorded responsibility spans from
time for which no visible assignment evidence exists.

A screenshot-only timeline would be misleading: event order, relation meaning,
responsibility intervals, authorization, and provenance must be explicit data
contracts. The implementation must also preserve the existing rule that a
stored `follows` or `related_to` link is not automatically a causal claim.

## Decision

1. PostgreSQL remains authoritative. Add a normalized project identity and
   three dependent tables: `project_history_project`,
   `project_history_event`, `project_event_relation`, and
   `project_responsibility_assignment`.
2. Every event, relation, and assignment requires an evidence `source_post`.
   Buyer reads apply the existing `post_read`, corporate visibility, draft,
   and deletion gates before projection.
3. A relation is returned only when both event endpoints and the relation's own
   evidence post remain visible. `causal` is always `false` in this contract.
4. Handover gaps are computed from the union of visible responsibility
   intervals. They are labelled visible-evidence gaps, not proof that no work
   occurred.
5. API timestamps are offset-aware RFC 3339 values. Naive timestamps fail
   closed rather than inheriting the host timezone.
6. The existing post detail popup embeds one `ProjectHistoryPanel`; no new GNB
   destination or second product shell is introduced. Multiple project keys
   require an explicit selector.
7. OWL-Time and PROV-O are an interoperable RDF projection only. The profile
   specializes temporal entities, associations, and activity-to-evidence usage without
   replacing relational authorization or inventing facts.

## Consequences

Buyers can inspect the complete visible project lifecycle, trace a current VOC
back to explicit earlier relations and source posts, and see responsibility
coverage and evidence gaps on one surface. Hidden evidence cannot leak through
an endpoint, relation, person, date, or derived gap. The read model remains
bounded and marks truncation rather than presenting a partial history as
complete.

The first implementation intentionally accepts only source-post-backed events.
Direct SAP, issue-ticket, and external-system event adapters remain future
writers into the same normalized contract; they may not bypass the evidence
and authorization boundary.

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals.
*Communications of the ACM, 26*(11), 832–843.
https://doi.org/10.1145/182.358434

Cox, S., & Little, C. (Eds.). (2017). *Time ontology in OWL* (W3C
Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/2017/REC-owl-time-20171019/

Klyne, G., & Newman, C. (2002). *Date and time on the Internet: Timestamps*
(RFC 3339). RFC Editor. https://doi.org/10.17487/RFC3339

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology* (W3C Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/2013/REC-prov-o-20130430/
