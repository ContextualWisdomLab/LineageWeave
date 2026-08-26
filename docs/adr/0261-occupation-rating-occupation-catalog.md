# ADR 0261: Imported occupation catalog for rating evidence

- Status: Accepted
- Date: 2026-08-27
- Extends: ADR 0257, ADR 0258, ADR 0259, ADR 0260

## Context

ADR 0260 removed typed release and source-table codes, but occupation
selection still requires an exact O*NET-SOC code. That makes a valid product
action depend on repository knowledge and allows a user to request an
occupation that has no observation in the selected source. The normalized
store already owns `occupational_classification_entry` titles and the
observation identities that prove a source actually describes an occupation.

## Decision

1. Add an authenticated read endpoint that lists occupations with at least
   one persisted observation in one exact imported rating source. Return the
   official O*NET-SOC code and occupation title. Exclude occupations that
   exist only as classification rows, and treat the Scales Reference support
   artifact as unavailable.
2. Order by published title then code. Bound the catalog; do not rank,
   recommend, or infer similarity. The catalog describes current database
   state, not the complete official O*NET occupation list.
3. Distinguish an unavailable source from an available source with no
   selectable occupation. Authentication matches ADR 0258.
4. The Dashboard occupation control is a native select populated only from
   this catalog for the currently selected source. Changing the source
   reloads and resets the occupation. If the occupation catalog is loading,
   empty, or unavailable, disable profile submission and give the next
   action. Do not retain a typed SOC fallback.
5. Display the published occupation title with the retained code on the
   opened profile. Derive no ranking or recommendation.

## Consequences

Users select a published occupation that the chosen source actually
describes. An unavailable or empty occupation catalog cannot masquerade as a
typed code. Adding an official occupation remains an importer operation with
digest and row-count validation rather than a UI-created catalog row.

## References

National Center for O*NET Development. (2026). *O*NET 31.0 database* [Data
set]. https://www.onetcenter.org/database.html
