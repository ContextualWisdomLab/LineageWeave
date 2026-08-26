# ADR 0261: Occupations represented by an imported rating source

- Status: Accepted
- Date: 2026-08-27
- Extends: ADR 0257, ADR 0258, ADR 0260

## Context

The source catalog removes internal release/source entry, but ADR 0260 still
leaves users to type an O*NET-SOC code. The normalized store already preserves
the source occupation title and code. A release may contain occupations that
are absent from one rating artifact, so the release classification alone is
not sufficient evidence that a profile exists for the selected source.

## Decision

1. Add an authenticated read endpoint returning stored O*NET-SOC code/title
   pairs that have at least one observation in one exact imported rating
   source. Keep unavailable source distinct from an available empty source.
2. Join by normalized release/code identity and an observation-existence
   predicate. Do not bind occupations by title similarity, keyword inference,
   external search, or a locally reconstructed classification.
3. Order by the stored occupation title and then code. Return the complete
   represented set because the official imported classification is the
   authoritative finite selector domain; do not introduce an arbitrary result
   cutoff that makes valid occupations disappear.
4. Replace free-text occupation-code entry with a native select whose visible
   label begins with the stored title and retains the exact code. Changing the
   rating source clears both occupation selection and displayed evidence.
5. While the occupation catalog is loading, empty, or unavailable, disable
   profile submission and state the next action. Pagination remains bound to
   the identifiers returned by the loaded profile under ADR 0259.

## Consequences

Users choose an occupation by its authoritative title without knowing an
internal code, while API requests continue to carry exact stable identifiers.
Employer job families and series remain outside this selector until their
separate authorized import contract exists.

## References

National Center for O*NET Development. (2026). *O*NET 31.0 database* [Data
set]. https://www.onetcenter.org/database.html
