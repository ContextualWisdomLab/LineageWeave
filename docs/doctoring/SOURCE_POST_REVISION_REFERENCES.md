# Source-post revision standards and research traceability

**Status:** Active PR evidence; not protected-main truth until merge.  
**Scope:** Migration 0024, ADR 0025, `GET /api/posts/{id}?as_of=`, and the
opened-post cutoff comparison.

## Standards mapped to implementation

| Source | Product implication | Implemented evidence |
|---|---|---|
| W3C PROV-O `wasRevisionOf` | Keep each rewrite as an identifiable revision of the same entity instead of overwriting the only stored sentence. | `source_post_revision` rows keyed by `post_id` + `written_at`; live `source_post` remains the current entity. |
| W3C Time Ontology in OWL | Do not collapse the analysis cutoff with the source write clock. | `written_at` / `superseded_at` live on the revision; `knowledge_cutoff` stays on `analysis_run`. `as_of` selects the covering interval. |
| Jensen & Snodgrass (1999) valid time | Use a half-open interval so exactly one revision is current at a clock. | Coverage is `written_at <= as_of` and (`superseded_at` is null or `superseded_at > as_of`). |
| ISO 8601-1:2019 | Parse `as_of` as a timezone-aware timestamp. | `parse_as_of_clock` treats `Z` and naive values as UTC; invalid clocks are 422. |
| ADR 0013 registry boundary | Do not store raw posts on the analysis-run payload. | `GET /api/analysis-runs/{id}` still returns titles and clocks only. The known body is on the opened post. |

## Temporal reasoning

A revision answers "what title and body were current at this source
clock." A run cutoff answers "what that analysis was allowed to know."
Selecting `as_of = knowledge_cutoff` is a join in the product, not a
column on `source_post_revision`.

## Privacy boundary

Revisions store the same purpose-bound source title and body already on
`source_post`. They do not belong in the analysis-run registry, audit
event, or home list. Necessary PII stays in the authorized post read.
A missing revision is omitted rather than masked or invented.

## Verification matrix

| Claim | Falsifiable test |
|---|---|
| Insert records a revision | After insert, one current `source_post_revision` matches title/body/`updated_at`. |
| Rewrite supersedes | A title or body update sets `superseded_at` and inserts a new current row. |
| Clock-only update is silent | Changing only `updated_at` does not add a revision. |
| Cutoff cover is exact | `as_of` between write and rewrite returns the earlier body; later `as_of` returns the live rewrite as `known_at` or omits when only the live row is asked. |
| Missing cover is omitted | `as_of` before the first `written_at` has no `known_at`. |
| Run detail stays aggregates | Analysis-run JSON has no `post_body`. |
| Seed is comparable | Demo public January sentence ≠ live later-window sentence. |

## APA 7th references

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management.
*IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44.
https://doi.org/10.1109/69.755613

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-O: The PROV ontology*
(W3C Recommendation). World Wide Web Consortium.
https://www.w3.org/TR/prov-o/

World Wide Web Consortium. (2022). *Time ontology in OWL* (W3C
Recommendation). https://www.w3.org/TR/owl-time/
