# ADR 0144 — Customer Master surfaces ADR 0010 counterparty entities through a write-time, provenance-bearing observation link, not read-time catalog traversal

**Decision status:** Proposed
**Date:** 2026-08-23

> Numbering note: this repository currently has multiple in-flight branches
> assigning ADR numbers in parallel (confirmed: `docs/adr/0143-lineage-isolation-reason.md`
> exists on an unmerged branch as of this writing). `0144` was the next free
> number on `docs/customer-master-scope-adr` at time of writing and may need
> renumbering when branches converge -- this is a known, separately tracked
> coordination gap (see `docs/product-technical-gap-baseline.md` on the
> `docs/customer-master-scope-adr` / `main` divergence), not a defect in this
> decision's content.

## Context

`/api/customer-master`'s `entity_rows` query (`backend/app/main.py`,
`read_customer_master`) already admits an entity through `own_affiliation`
(`account_affiliation`, the ABAC boundary — Hu et al., 2019) or, since ADR
0125, `observed_organization`: an entity directly mentioned in a visible,
eligible post reaches the tree with no affiliation row at all. It still
cannot surface a counterparty's ancestor chain when the ancestor itself was
never named in any post this account can read — only inferred as a parent by
ADR 0010's verified hierarchy-inference pipeline
(`corporate_entity_ingestion.py`). ADR 0125 §5 renders that child as a tree
root rather than widen access to complete it, so an `AUTO-`-created
counterparty's real, verified `parent_entity_id` chain can never reach any
account's view, because `account_affiliation` is never written for entities
ADR 0010 creates.

This ADR does not reopen ADR 0125's own/granted-vs-observed filtering
(`scope_facets` already ships that). It closes the remaining gap only: how a
verified ancestor chain reaches `entity_rows` without becoming a general
corporate-entity directory that leaks organizations never mentioned in
anything a given account can see.

Two designs were proposed and adversarially critiqued for ABAC safety: (A) a
bounded, read-time recursive traversal of `parent_entity_id` gated on ADR
0010's `AUTO-` code prefix; (B) a write-time `account_observed_entity` link
table populated at ingestion from the same post-read authorization check the
endpoint already trusts.

## Decision

**Adopt Proposal B — the write-time `account_observed_entity` link table —
with its critique's fix folded in as a required part of the design, not an
optional hardening pass.** Proposal A is rejected outright (detail in
Rejected Alternatives): its critique found a real cross-account leak, not a
cosmetic gap.

B's own critique found only a materialized-cache staleness bug:
`account_observed_entity` is written from a correct, one-time evaluation of
the real ABAC predicate, but the read-time join in the original design
revalidates only the affiliation side (`granting_corporate_entity_id`),
never the post's own mutable eligibility (`corporate_entity_id`
reassignment, `visibility_code` tightening, `source_detail_state_code`
flipping to a restricted state, deletion). This ADR adopts B **only** with
that gap closed: reconciliation must re-run the full authorized-account-set
computation, triggered synchronously off the post-mutation paths that can
narrow eligibility, with nightly full-corpus reconciliation kept only as a
backstop for missed events (DeCandia et al., 2007, on bounding, not
eliminating, staleness in a materialized read path).

## Consequences

**Positive.** An ADR-0010-created counterparty and its real parent chain
reach Customer Master once observed in a readable post, with no per-request
traversal query. Correctness stays pinned to the one ABAC predicate the
endpoint already trusts, evaluated once at ingestion and re-evaluated only
on events that can change its answer — not reimplemented as a bespoke
read-time graph walk. The link table is small and audit-friendly:
`granting_corporate_entity_id` and `source_post_id` make every surfaced
entity traceable to the grant and post that justified it.

**Negative.** This is a write-amplifying background system, not a pure query
change — a new table, a new ingestion hook, and a mutation-triggered
reconciliation path that must track `SOURCE_POST_VISIBILITY_SQL` /
`source_post_state_visibility_sql` wherever those predicates next change.
Staleness is bounded, not zero: between a post's eligibility-narrowing
mutation and the next reconciliation pass, an account can still see an
entity sourced from a post it can no longer read. Accepted as a monitored
risk targeting synchronous closure, not treated as solved.

## Rejected Alternatives

**Proposal A — bounded ancestor-chain traversal gated on the `AUTO-`
namespace.** Rejected as a class. `corporate_entity` is one catalog shared
across every account, and `get_or_create_corporate_entity` reuses an
existing row on a fuzzy match or `on conflict (corporate_entity_code)`
rather than re-deriving it from the post that triggers a given traversal.
An ancestor's `entity_name` and `parent_entity_id` can therefore have been
established entirely from one account's private post, while the `AUTO-`
prefix proves only that the *edge* is publicly corroborated — not that
*this* account's evidence taught LineageWeave the fact (Denning, 1976, on
conflating a fact's truth with the right to see how it was learned). An
unrelated account's traversal can then surface it: a structural leak, not a
tunable edge case. The critique's own suggested repair — gate each hop on
the account's own visible-evidence predicate — is directionally correct,
but applying it makes A behave exactly like ADR 0125 §5's existing
root-fallback: an ancestor this account never itself observed still renders
as a root. A safe A closes nothing this ADR needs closed; an unsafe A leaks.
B is the only design that both adds the missing capability and survives its
own critique with a bounded, well-understood fix.

## Implementation Notes

1. New table `account_observed_entity(account_id, corporate_entity_id,
   granting_corporate_entity_id, source_post_id, first_observed_at,
   last_observed_at, observation_count)`, unique on `(account_id,
   corporate_entity_id)`.
2. Hook the write into the existing `get_or_create_corporate_entity` call
   sites (`keyman_ingestion.py`, `post_summary_ingestion.py`,
   `customer_hint_ingestion.py` — the sites ADR 0010 already wired), not a
   third path. On resolving or creating a counterparty `corporate_entity_id`,
   compute the post's authorized-account set with the predicate
   `read_customer_master` already applies, and upsert one row per account.
3. `entity_rows` becomes a `UNION` of the existing
   `account.corporate_entity_ids` scope and an `account_observed_entity ⋈
   account_affiliation ON (account_id, granting_corporate_entity_id)` scope,
   tagged into ADR 0125's existing `observed_organization` /
   `observed_hierarchy` facets — a materialization strategy, not a new
   evidence class, so no new facet is needed. No per-ancestor row: ADR 0010
   already populates `parent_entity_id` at creation time (bounded 4-level
   resolution), and the query walks it the same way it already walks the
   affiliation parent chain.
4. Reconciliation, both parts required: (a) affiliation-side revocation is
   already live via the join in step 3, no lag; (b) post-side narrowing
   fires the step-2 recomputation synchronously off the post-mutation path
   (reuse this repo's durable-outbox pattern, as in `POST
   /api/analysis-runs/{id}/start`) and prunes rows for accounts no longer in
   the recomputed set; nightly full-corpus reconciliation, reusing the
   customer-hint bulk-backfill script's batch shape, is a backstop for
   missed events only.
5. Tests required before wiring the query: an ingestion-time test that the
   write-time account set matches `read_customer_master`'s predicate
   exactly, so the two call sites cannot silently drift; a mutation test
   that narrowing a post's visibility prunes its links within one
   synchronous cycle; an `entity_rows` test that a private post's
   counterparty never appears for a non-authorized account across
   grant/redaction race orderings.

## References (APA 7th)

DeCandia, G., Hastorun, D., Jampani, M., Kakulapati, G., Lakshman, A.,
Pilchin, A., Sivasubramanian, S., Vosshall, P., & Vogels, W. (2007). Dynamo:
Amazon's highly available key-value store. *ACM SIGOPS Operating Systems
Review, 41*(6), 205–220. https://doi.org/10.1145/1323293.1294281

Denning, D. E. (1976). A lattice model of secure information flow.
*Communications of the ACM, 19*(5), 236–243.
https://doi.org/10.1145/360051.360056

Hu, V. C., Ferraiolo, D., Kuhn, R., Schnitzer, A., Sandlin, K., Miller, R., &
Scarfone, K. (2019). *Guide to attribute based access control (ABAC)
definition and considerations* (NIST Special Publication 800-162, updated
2019). National Institute of Standards and Technology.
https://doi.org/10.6028/NIST.SP.800-162
