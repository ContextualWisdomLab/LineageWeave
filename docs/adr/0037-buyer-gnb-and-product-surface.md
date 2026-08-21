# ADR 0037: Buyer GNB and product-facing frontend surface

- Status: Accepted
- Date: 2026-08-18

## Context

The frontend currently combines buyer evidence browsing with analysis-run,
period-report, TEPP, and orchestration controls. This makes the primary screen
look like an LLM laboratory and leaves related records difficult to open from
entity and Keyman evidence. PR #251 defines the buyer information architecture,
but its branch is a draft based on PR #74 and cannot be treated as a reason to
bypass protected-branch review.

## Decision

The authenticated frontend uses the four-destination buyer GNB from #251:

1. Board
2. Customer master
3. Calendar
4. Ask Agent

The Board remains the default destination. Post titles in the Board, Event
Lineage, and related entity/Keyman evidence are direct controls that open the
post detail popup. Related posts are an evidence trail, not a decorative list.

The destinations use existing authorized contracts until the independent
services are available:

- Customer master reads the current account's authorized corporate entities
  from `/api/me`.
- Calendar reads existing post commitments from `/api/calendar` and opens the
  selected source post.
- Ask Agent requires an authorized source post and reuses the existing
  post-scoped grounded chat contract.

Analysis runs, period reports, and rebuild controls are not part of the open
buyer surface. They remain under a collapsed advanced-review section so
existing operational access is not discarded while the product surface is
being separated.

The frontend supports Korean, English, Chinese, Japanese, and Vietnamese via
the local i18n layer. No raw LLM endpoint is called from the browser.

This decision ports the required product behavior into the current semantic
branch. It does not force-merge #74 or merge the draft #251 branch; protected
branch review and current-head checks remain mandatory.

## Consequences

- Buyer navigation is stable and discoverable without exposing analysis
  internals in the default view.
- Customer, calendar, and Ask Agent screens show real authorized data rather
  than placeholder or fabricated records.
- A future CalDAV contract and global source-grounded Ask Agent contract can
  replace the current adapters without changing the GNB.
- The advanced-review section is transitional and should be removed or moved
  to an operator route once the operational UI has a dedicated boundary.
