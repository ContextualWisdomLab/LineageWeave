# ADR 0225: Ask answers link citations to an evidence timeline

- Status: Accepted
- Date: 2026-08-26
- Related: [0039](0039-global-ask-agent-source-boundary.md), [0090](0090-global-ask-lineage-timeline-expansion.md), [0153](0153-ask-evidence-layer-popup.md), [0202](0202-ask-event-time-filter.md)

## Context

Global Ask returns an answer and authorized cited posts, but the answer and
source controls are visually separate. A reader cannot select citation `[2]`
and land on the corresponding event, or select an event and return to the
answer citation. The current response also omits the cited source's observed
instant and named clock, so the frontend cannot construct an honest event-time
list without guessing from the lineage graph.

## Decision

1. A Global Ask result returns `cited_events` in citation order. Each entry is
   derived from the same authorized `ChatSourceDocument` that was admitted to
   the answer and contains only its post id, title, persisted observed instant,
   and clock code. `event_occurred_at` is preferred; `created_at` is the named
   fallback. A missing instant remains absent.
2. The answer renders citations `[1]..[n]` from `cited_posts`/`cited_events`.
   Selecting a citation focuses and highlights its event card. Selecting that
   card focuses and highlights the matching citation. Both directions preserve
   the citation number even when cards are chronologically ordered.
3. Every event card opens the existing evidence layer and the authorized full
   post. The cards show the named source clock and stored evidence; they do not
   expose provider, package, schema, hash, environment, or model-run detail.
4. This surface is an **answer evidence timeline**, not a Project Journey.
   Chronological ordering alone does not create a predecessor, branch, project
   start, or causal relation. The separate Project Journey contract continues
   to require a persisted TEPP TDT/CHRONOS result under ADR 0206.
5. A commercial perspective or recommended response may appear only inside the
   contextual-orchestrator answer when the cited event progression supports it.
   The frontend never manufactures a recommendation from dates, titles, or
   citation order. Customer copy tells the reader which evidence or source to
   inspect next and does not explain internal implementation boundaries.
6. The interaction uses native buttons, visible focus, `aria-pressed`, a live
   selection status, no color-only state, and no animated scrolling. It remains
   a single column on narrow viewports and a conversation/timeline split when
   space permits.

## Consequences

- The reader can move between an answer claim and its source event without
  losing context.
- Event time and record time remain distinguishable without inventing dates.
- Existing evidence-popup and post-detail authorization paths remain the only
  source-opening paths.

## Verification

- Backend tests prove citation-order preservation, clock selection, absent-time
  behavior, and unknown-citation removal.
- Component and Storybook interaction tests prove both focus directions,
  source opening, keyboard semantics, empty time, narrow layout, and
  customer-facing copy.
- Authenticated Compose screenshots cover desktop and narrow viewports with
  synthetic data.

