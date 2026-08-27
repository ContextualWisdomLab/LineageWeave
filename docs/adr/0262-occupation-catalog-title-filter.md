# ADR 0262: Occupation catalog title filter

- Status: Accepted
- Date: 2026-08-27
- Extends: ADR 0259, ADR 0260, ADR 0261

## Context

ADR 0261 replaced typed O*NET-SOC entry with a native select of occupations
that have observations in the chosen source. An official rating artifact can
cover hundreds of occupations, so a user still cannot find a published title
without scanning the full catalog. A free-typed code would reintroduce the
gap ADR 0261 closed.

## Decision

1. Keep the occupation control as a native select populated only from the
   imported occupation catalog for the selected source.
2. Add a native search field that filters that catalog by case-insensitive
   substring of the published title or retained O*NET-SOC code. Do not rank,
   boost, or infer similarity.
3. If the filter matches no catalog row, disable profile submission and give
   a next action. If the current selection leaves the filtered set, move to
   the first remaining catalog identity or clear the selection.
4. Reset the filter when the source or occupation catalog reloads. Never
   submit a value that is not in the loaded catalog.
5. Authentication, provenance, and fail-closed unavailable/empty catalog
   states remain ADR 0261.

## Consequences

A user can find a published occupation by title without typing an internal
code and without treating filter order as a recommendation.

## References

National Center for O*NET Development. (2026). *O*NET 31.0 database* [Data
set]. https://www.onetcenter.org/database.html

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/
