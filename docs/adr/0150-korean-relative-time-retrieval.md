# ADR 0150: Global Ask resolves Korean relative-time expressions

- Status: Accepted
- Date: 2026-08-22
- Related: [0047](0047-global-ask-semantic-retrieval.md), [0090](0090-global-ask-lineage-timeline-expansion.md), [0183](0183-ask-event-time-filter.md)

## Context

A question like "어제 무슨 일이 있었나요?" ("what happened yesterday?") names a
time window the reader already has in mind. Before this decision,
`gather_global_chat_sources`'s keyword retrieval (ADR 0047) had no way to
use that window: "어제" only ever became a literal search token against
post titles and bodies, indistinguishable from any other two-character
term. A fresh, unrelated post that happened to rank highest on unrelated
keyword overlap could outrank the post the reader actually meant.

## Decision

`lineageweave.temporal_expressions.resolve_korean_relative_time` is a pure
date-arithmetic function (no database or network access) that resolves a
question's first Korean relative-time expression into an inclusive
`(start_date, end_date)` window. It covers 오늘/어제/그제(그저께)/그끄제(그끄저께),
작년/재작년/올해/내년, 작년·재작년 이맘때(쯤) (a ±5-day fuzz window around the
anniversary date, since "-쯤" means "approximately"), 지난/이번/다음 주/달, and
the general "N일/주/개월/년 전" pattern. "언젠가" ("someday") resolves to no
bound -- the reader has explicitly declined to name one, which is the same
retrieval behavior as finding no expression at all.

`gather_global_chat_sources` applies the resolved window as an additional
event-time bound on its final ABAC-filtered candidate query (ADR 0183:
`coalesce(event_occurred_at, created_at)`), additive to the existing
keyword-match ranking -- it narrows the already-ranked candidate set, it
does not replace ranking with a date filter. Cited sources name which
clock matched. Matched temporal literals are excluded from keyword-term
extraction (`TEMPORAL_STOPWORDS`) so a resolved expression does not also
become a near-meaningless literal search term.

## Considered alternatives

- Send the raw question to an LLM to extract a date range: rejected for the
  same reason ADR 0047's keyword step avoids ungrounded LLM inference at
  the retrieval boundary -- a hallucinated date range would silently
  narrow (or widen) the candidate set with no way for the reader to verify
  it, and every extra provider round-trip is retrieval latency the reader
  pays before seeing an answer.
- Resolve to a single anchor day for the generalized "N주/N개월 전" pattern
  (mirroring "N일 전"): rejected -- "2 weeks ago" means that whole week to
  a reader, not one arbitrary day inside it, so `_week_range`/`_month_range`
  are used instead, matching how the named "지난주"/"지난달" patterns already
  behave.

## Consequences

- Global Ask can now answer time-scoped questions without the relative-time
  term itself acting as retrieval noise.
- The resolver is locale-specific (Korean only); a question in another
  supported UI locale (ADR on i18n scope, `frontend/src/i18n.ts`) that
  names a relative time in that language still falls back to keyword-only
  retrieval. Extending to additional locales is a follow-up, not required
  by this decision.
- `today` is always passed explicitly by the caller (server-local date);
  the resolver itself never reads the wall clock, keeping it a pure,
  trivially unit-testable function.
