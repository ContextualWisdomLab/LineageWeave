# ADR 0259: Occupation-rating evidence in the existing Dashboard

- Status: Accepted
- Date: 2026-08-27
- Extends: ADR 0183, ADR 0206, ADR 0258
- Figma file ID: `1Su3lDRmiZdcUs47t1QwIX`

## Context

ADR 0258 makes an exact imported occupation profile readable, but an API does
not let an authenticated user find a published work characteristic or notice
that a value has low precision. ADR 0183 fixes the analyst GNB and prohibits a
new destination for every evidence type. The existing Dashboard is the place
for evidence-oriented next actions and already owns responsive table and form
tokens under ADR 0206.

## Decision

1. Add the occupation profile below the existing operations evidence on the
   Dashboard. Do not add or rename a GNB destination.
2. Require the user to submit an exact O*NET-SOC code, data release, and source
   table. Native form validation rejects malformed occupation codes before a
   request; the API remains the trust-boundary validator.
3. Show each exact published value beside its declared scale bounds, optional
   category, sample size, standard error, confidence interval, source month,
   domain source, suppression warning, and not-relevant flag. Do not calculate
   a score, rank, weight, trait estimate, or recommendation.
4. Keep `source unavailable` distinct from `occupation has no observations`.
   Both states give a next action instead of displaying zero or a blank table.
5. Link the rating artifact and scale definition. The API carries their
   digests and row counts for provenance; a later disclosure control may show
   those identifiers when user research demonstrates that it aids the task.
6. Reuse the existing Dashboard Figma file, design tokens, native controls,
   responsive overflow, focus behavior, and reduced-motion baseline. The table
   has a named keyboard-focusable region and every warning is text, not color.
7. Storybook records populated, narrow, source-unavailable, and empty-profile
   scenes using synthetic records only. Runtime screenshot review covers the
   populated desktop and narrow scenes.

## Consequences

Users can inspect source evidence without confusing absence, low precision, or
not-relevant responses with a negative occupational conclusion. The interface
does not introduce a local psychometric or inference implementation.

## References

National Center for O*NET Development. (2026). *O*NET 31.0 database* [Data
set]. https://www.onetcenter.org/database.html

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/
