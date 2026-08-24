# ADR 0025 — Source-post revisions keep the cutoff-known body

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

ADR 0016 marks in-cutoff titles whose live `updated_at` is after
`analysis_run.knowledge_cutoff`. After `make seed`, Demo public post was
marked rewritten while the live sentence stayed the January text, so the
operator was told to compare bodies and was given two clocks, not two
texts.

The analysis-run registry must not store raw posts (ADR 0013). A missing
cutoff body and a confidently-reconstructed body are different things:
do not invent the earlier sentence on the run detail.

W3C PROV-O `wasRevisionOf` (Lebo et al., 2013), W3C Time Ontology
in OWL (World Wide Web Consortium, 2022), and temporal valid-time
intervals (Jensen & Snodgrass, 1999) keep the write history on the
source row, half-open `[written_at, superseded_at)`.

Migration 0021 is reconstruction, 0022 is snapshot membership, 0023 is
the start outbox, and ADR 0024 seeds the period-report run. This is the
next free slot.

## Decision

Migration `0024_source_post_revision.sql` adds `source_post_revision`
(3NF: one post, one title/body pair, one valid-time interval). A trigger
records a revision on insert and on title or body rewrite. Clock-only
updates do not pretend to be a rewrite.

`GET /api/posts/{id}?as_of=` returns `known_at` when a revision covers
that clock. The live `post_body` stays the live row. A missing cover is
omitted. Analysis-run detail stays titles and clocks.

`make seed` writes the January Demo public sentence, then rewrites it on
2026-01-13 so the opened marked title shows both texts.

## Consequences

- After `make seed`, open **Lineage reconstruction · Succeeded · Demo
  Corp**, then Demo public post: **Body this run knew** is the January
  follow-up; the live body names the later delivery window.
- Demo private post stays unmarked and has no second text.
- Roll back `0024` before `0023` / `0022` / `0021` / `0020` / `0018`.
- TEPP stays behind `tepp_client`. This write does not invent a theta.

### Correction (2026-08-24)

This ADR previously misattributed the W3C PROV-O Recommendation as
"Moreau, L., & Missier, P. (Eds.). (2013)." Luc Moreau and Paolo
Missier are real W3C editors, but of PROV-O's sibling document,
*PROV-DM: The PROV data model* -- also a W3C Recommendation published
the same day, 30 April 2013 -- not of PROV-O itself. PROV-O's actual
editors, per the document at the cited URL, are Timothy Lebo, Satya
Sahoo, and Deborah McGuinness. The title and URL were already
correct -- `prov:wasRevisionOf`, the term this ADR actually relies
on, does live at that address -- only the editor names had been
swapped in from the neighboring same-day spec. The citation is
corrected here to Lebo, Sahoo, & McGuinness (2013); no change to the
decision or the `wasRevisionOf`-based design follows from this fix.

## References

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management.
*IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44.
https://doi.org/10.1109/69.755613

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The
PROV ontology* (W3C Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/prov-o/

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/
