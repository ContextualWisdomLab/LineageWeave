# ADR 0021 — Source-post write clock honors explicit pins

**Decision status:** Accepted
**Date:** 2026-08-16

## Context

ADR 0016 compares live `source_post.updated_at` with
`analysis_run.knowledge_cutoff` so the operator can see which in-cutoff
titles were rewritten after the run. The column defaulted to `now()` on
insert and never moved on a later title or body write, so a real rewrite
stayed unmarked and `make seed` could not pin Demo public post to
2026-01-13 unless every statement assigned `updated_at`.

W3C Time Ontology in OWL (Hobbs & Pan, 2017) and ISO 8601-1:2019 keep
the live write clock distinct from the analysis cutoff. A missing write
clock and a confidently-in-cutoff clock are different things.

## Decision

Migration `0021_source_post_write_clock.sql` adds
`touch_source_post_write_clock` on `BEFORE UPDATE` of `source_post`.
The trigger bumps `updated_at` to `clock_timestamp()` only when
`post_title` or `post_body` changes and the statement did not already
assign `updated_at`. Thread-group, visibility, or grouping-key updates
do not pretend to be a rewrite.

`make seed` may still pin Demo public post to 2026-01-13 and Demo
private post to its create clock. A later product body edit after the
January cutoff marks the title.

## Consequences

- After `make seed`, open the Demo Corp lineage run: Demo public post
  is marked updated after cutoff; Demo private post is not.
- Open a marked title: the live popup names both clocks. ADR 0022
  then shows the cutoff-known body beside the live rewrite.
- Roll back `0022` before `0021` / `0020` / `0018` when emptying a
  database that also uses the retention purge.

## References

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Hobbs, J. R., & Pan, F. (2017). *Time ontology in OWL* (W3C
Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/2017/REC-owl-time-20171019/

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/
