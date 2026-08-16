# ADR 0024 — Home list accessible names include the visible next facts

**Decision status:** Accepted on this active PR; not protected-main truth until merge
**Date:** 2026-08-16
**Depends on:** ADR 0014 analysis-run list AccName
**Refs:** Issue #79 (Milestone 2 parent); WCAG 2.2 SC 4.1.2

## Context

ADR 0014 put the analysis-run next-action sentence in the list-button
accessible name after `aria-label` hid it. The same replacement still
hid the next facts on the other home lists:

- Calendar heard only the post title, not the commitment, status, or due date.
- Period-index buttons heard only the week code, not mean θ or the FIPC delta.
- Report-member buttons heard only the post title, not θ, ticket, or due date.
- Grouping-comparison buttons heard the raw `grouping_kind` wire code.
- The post list heard only the title, not VOC or visibility.

A buyer using a screen reader could not choose the commitment that is
due or the report post with the higher θ.

Parallel PRs may claim ADR 0021 (person catalog) and ADR 0023
(analysis-run home tokens). This decision uses the next free slot.

## Decision

Home list `aria-label` values include the same facts the sighted
operator already sees:

- Calendar: `Open commitment for: {post}. {summary}. {status}. due {date}`
- Period index: `Open report period {code}. mean θ {n}. {delta or shared metric}. CAT: …`
- Report member: `Open report post: {title}. θ {n}. {ticket}. {status}. due {date}`
- Comparison: `Compare {kind label}: {label}. mean θ {n}. {count} posts`
- Post list: `View post: {title}. {voc label}. {visibility label}.`

Copy uses lookup labels, not raw status or grouping wire codes. This
slice does not invent a theta, start reconstruction, or add a TEPP
transport.

## Consequences

After `make seed`, the Demo Corp commitment name includes
`due 2026-01-12`, the 2026-W03 period name includes `vs 2026-W02: +0.92`,
and the Public post list name includes Voice of Customer and Public.
Analysis-run AccName stays ADR 0014. Digest hover disclosure stays a
later slice.

## References

World Wide Web Consortium. (2018). *Accessible name and description
computation 1.1* (W3C Recommendation).
https://www.w3.org/TR/accname-1.1/

World Wide Web Consortium. (2023). *Web content accessibility
guidelines (WCAG) 2.2* (W3C Recommendation).
https://www.w3.org/TR/WCAG22/
