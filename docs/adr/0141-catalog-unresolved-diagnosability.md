# ADR 0141 — Catalog-unresolved reason is explicit, not one flat label

**Decision status:** Proposed
**Date:** 2026-08-22

## Context

`docs/product-technical-gap-baseline.md` (§5, "R&R role/relationship
conflation and catalog-linking boundary") records a live UI/UX finding:
"카탈로그 미연결" ("Not linked to catalog", `frontend/src/i18n.ts`) is the
correct, honest label whenever a role's `catalog_node_id` is `null`
(`fetch_persisted_summary`, `backend/app/post_summary_ingestion.py`), but it
gives the reader no way to tell apart the reasons that null can happen:

- An organization actor's mention tied two or more equally-similar catalog
  candidates (`RESOLUTION_TIE`, `score_corporate_entity`,
  `lineageweave/corporate_hierarchy_resolution.py`; ADR 0026 — a tie must
  stay unbound, never first-win a homonym).
- `get_or_create_corporate_entity`'s `inference_client` or
  `verification_client` (`backend/app/corporate_entity_ingestion.py`)
  defaulted to a `Null*Client` because no live contextual-orchestrator /
  SearXNG transport is wired in this environment — in that state the
  function can only match an *already-cataloged* entity, never create one.
- A live client was available and was actually called, but hierarchy
  inference proposed nothing, or verification declined to corroborate the
  proposed placement (`placement_result.status_code != STATUS_CORROBORATED`)
  — a considered "no" rather than an unattempted check.
- A person actor's name has no matching `cataloged_person` row yet
  (`_resolve_existing_cataloged_person_id`) — ADR 0009 forbids inventing one.

These are different facts a reader would act on differently ("try again once
the orchestrator is configured" vs. "this was checked and is not the same
entity" vs. "wait for another mention to disambiguate the tie"), but today
they are indistinguishable from the UI. This is a genuine information loss:
the resolution kind (`unique` / `tie` / `miss`) and the client-availability
state already exist as in-memory facts inside
`get_or_create_corporate_entity` and `_resolve_affiliated_organization` for
the duration of one call — they are simply discarded before
`_replace_summary_projection` persists the row.

Per AGENTS.md, a schema/behavior change needs its ADR before code. This is
the ADR for that change; it does not touch extraction, the summary contract,
or catalog creation itself (those are unrelated, separately-scoped changes —
see `docs/product-technical-gap-baseline.md` §5 items 2 and 3 for the ones
this ADR deliberately does not fix).

## Decision

1. Add two nullable, `common_lookup_value`-backed reason columns to
   `post_summary_role`, following the same pattern as ADR 0125's
   `affiliation_scope_code` (`migrations/0134_catalog_unresolved_reason.sql`):
   `catalog_unresolved_reason_code` (why the primary person/organization/team
   actor has no catalog link) and `affiliation_catalog_unresolved_reason_code`
   (why the role's *affiliated* organization,
   `cataloged_affiliated_corporate_entity_id` / ADR 0127, has none). Two
   columns, not one, because a role commonly has its primary actor resolved
   (a known person) while its affiliation is not, or vice versa — one shared
   column could not represent both states at once. The shipped "Not linked
   to catalog" label (`frontend/src/components/RoleEvidence.tsx`,
   `unresolvedLabel` prop) currently renders next to the *affiliation*
   field, so `affiliation_catalog_unresolved_reason_code` is the column that
   closes the gap-baseline finding as literally reported;
   `catalog_unresolved_reason_code` closes the same gap for the primary
   actor, which today shows no reason at all when unresolved. Each column is
   set only when its corresponding `cataloged_*_id` column is `null`; both
   stay `null` when a catalog link exists, and both stay `null` on
   historical rows written before this migration (no retroactive reason is
   invented for history — the frontend falls back to today's behavior, a
   plain name with no reason shown, when the reason is absent).
2. Closed vocabulary, four values:
   - `reason_tied_candidates` — `RESOLUTION_TIE`: two or more candidates
     shared the top similarity score.
   - `reason_no_live_client` — `inference_client.available` or
     `verification_client.available` was `False` (including the
     `HttpClientError` / `OSError` / `TimeoutError` catches that already
     exist in `get_or_create_corporate_entity`, which are the same "channel
     unavailable this run" fact as an unavailable client, not a decision).
   - `reason_not_corroborated` — a live client ran, but inference proposed
     nothing or verification returned a non-`STATUS_CORROBORATED` result.
   - `reason_no_catalog_entry` — the person-catalog name lookup
     (`_resolve_existing_cataloged_person_id`) found no row. This is the only
     reason code available to a person actor; the resolver has no client
     dependency to distinguish further, and inventing a finer distinction
     here would misrepresent what the function actually checked.
3. `get_or_create_corporate_entity` returns the reason alongside the id
   (`(catalog_id: str | None, reason_code: str | None)`) instead of just the
   id, so the caller can persist it without re-deriving state the callee
   already computed and discarded. `_resolve_affiliated_organization` grows
   a fourth return element carrying the same reason for the affiliation
   case (its Keyman-ingestion caller, a separate surface out of this ADR's
   scope, discards it unchanged). `_resolve_existing_cataloged_person_id`
   gains the equivalent single-reason return.
4. `fetch_persisted_summary`'s `payload_roles` entries add both
   `catalog_unresolved_reason_code` and
   `affiliation_catalog_unresolved_reason_code` (each `null` when linked or
   historical). `frontend/src/api.ts` extends the role type to carry both.
5. The frontend replaces the single `unresolvedLabel` string
   (`RoleEvidence.tsx`, wired from `frontend/src/App.tsx`'s R&R row
   renderer) with a small lookup from reason code to one of four specific,
   translated messages, falling back to today's plain rendering (no reason
   shown) when the reason is `null`. The primary actor's own name gains the
   same treatment where it currently shows no diagnostic at all. No
   confirmation dialog, retry button, or invented certainty is added — this
   is read-only diagnostic text.
6. This does not change ABAC/visibility, does not create a catalog row that
   wasn't already going to be created, and does not change the tie/miss/
   corroboration policy itself (ADR 0009, 0010, 0026 govern those). It only
   makes an already-computed-and-discarded fact visible.

## Considered alternatives

- **Do nothing; leave the flat label.** Rejected: the gap-baseline finding is
  that this is undiagnosable today, and the reader currently cannot tell "not
  yet possible to check" from "checked and declined."
- **Infer the reason at read time from current client configuration instead
  of persisting it.** Rejected: the reason is a fact about what happened
  *when the role was last persisted*, not about the reader's current
  environment. A role summarized while an orchestrator was configured, then
  read after it goes down, would get the wrong "no live client" reason. The
  reason must be captured at write time, not derived at read time.
- **One generic "insufficient evidence" code instead of four.** Rejected:
  the gap-baseline finding is specifically that a reader cannot act on an
  undifferentiated null; collapsing back to one bucket reproduces the same
  problem it exposed.

## Consequences

- Historical rows keep the honest gap ("we didn't record why") rather than a
  fabricated backfilled reason; only newly-persisted summaries get the
  specific code. This is consistent with how ADR 0125 handled its own
  migrated column.
- `get_or_create_corporate_entity`'s signature change is a small, mechanical
  ripple to its ~7 in-repo callers (`backend/app/keyman_ingestion.py`,
  `backend/app/post_summary_ingestion.py`) and its existing test suite
  (`tests/test_tied_organization_no_create.py` and the corporate-hierarchy
  resolution tests) — each call site now reads a tuple instead of a bare id.
  No test asserts on the old bare-id return shape in a way that survives
  unchanged; those tests are updated alongside the implementation.
- Keyman-side organization/affiliation resolution
  (`backend/app/keyman_ingestion.py`) can reuse the same reason vocabulary
  later if the same undiagnosability complaint is raised there; this ADR
  scopes only the R&R post-summary path the gap-baseline finding names.
