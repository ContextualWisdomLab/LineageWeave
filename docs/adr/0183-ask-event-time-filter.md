# ADR 0183 — Global Ask relative-time filters bind to event time

**Decision status:** Accepted
**Date:** 2026-08-24
**Related:** [0150](0150-korean-relative-time-retrieval.md), [0016](0016-analysis-run-knowledge-cutoff-posts.md), issue [#569](https://github.com/ContextualWisdomLab/LineageWeave/issues/569)

## Context

ADR 0150 resolves Korean relative-time expressions ("어제", "그저께",
"지난주") into an inclusive Seoul calendar window and applies that
window as a `created_at` bound on Global Ask retrieval. `created_at`
is the record ingestion timestamp (`prov:generatedAtTime` for the
stored post). Bulk imports cluster that clock near import time, so
"어제 무슨 일이 있었나요?" can miss the posts whose *events* fell
yesterday.

Five-W1H assembly already refuses to treat `created_at` as event
evidence (`lineageweave.five_w1h`). Reconstruct still reads the
fixture timeline through `created_at = occurred_at` on seed. Those
are different clocks. Collapsing them in Ask retrieval is the bug.

## Decision

1. Persist nullable `source_post.event_occurred_at` (two-or-more-word
   `snake_case`, 3NF). This is the source-system event instant when
   known. It is not a TEPP theta, not a 5W1H text claim, and not a
   knowledge cutoff.
2. Global Ask relative-time filters compare the Seoul calendar date of
   `coalesce(event_occurred_at, created_at)` against the ADR 0150
   window. Event time wins. Ingestion time is the documented fallback
   when the event instant is absent. Do not invent an event date.
3. When a relative-time window is active, each cited source discloses
   the matching axis as a buyer-visible evidence fact:
   - `time axis: event occurred at` when `event_occurred_at` is present
   - `time axis: record created at` when the filter fell back
   Open that cited post to read the fact. No time-axis fact is added
   when the question names no relative time.
4. Importers may map an authoritative source event-date column onto
   `event_occurred_at`. An unmapped import leaves the column null so
   Ask keeps the fallback and names it. Seed copies fixture
   `occurred_at` onto both clocks so reconstruct and leftover pairs
   stay on the designed January timeline.
5. Analysis-run knowledge cutoff (ADR 0016) continues to use
   `created_at`. Period-report week membership continues to use
   `created_at`. Those clocks answer "what the product had stored,"
   not "when the event happened."

## Considered alternatives

- Parse 5W1H `when` text into a date: rejected. Those slots are
  extractive claims, not a calendar type. A failed parse would
  silently widen or narrow retrieval.
- Replace `created_at` in place: rejected. Ingestion, cutoff, and
  period-report membership still need the record clock (Allen, 1983;
  W3C Time Ontology in OWL).
- LLM-extracted event dates at retrieval time: rejected for the same
  reason ADR 0150 rejected LLM date ranges.

## Consequences

- Clustered bulk imports keep yesterday's events retrievable.
- Readers can see which clock matched instead of guessing.
- Existing seed leftover pairs still sit above the member list; a
  click still opens that post.

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals.
*Communications of the ACM, 26*(11), 832–843.
https://doi.org/10.1145/182.358434

Hobbs, J. R., & Pan, F. (2017). *Time ontology in OWL* (W3C
Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/owl-time/

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The
PROV ontology* (W3C Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/prov-o/
