# Unreleased — SKOS organization alias catalog binding

## Added

- Corroborated SKOS `altLabel` / `prefLabel` pairs expand corporate
  catalog candidates so a synthetic short form (`AGP`) and full form
  (`Aurora Grid Power`) bind one `corporate_entity` row (ADR 0158).
  Uncorroborated pairs, short near-matches, and tied scores stay unbound.
  Real organization names are not used in fixtures.
