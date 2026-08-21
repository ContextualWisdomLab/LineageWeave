# External lineage analysis versioning policy

- `contract_version` follows semantic versioning independently from the LineageWeave package version.
- Unknown major versions fail closed.
- Additive optional fields require a new minor contract revision and corresponding consumer fixtures.
- Vocabulary changes, field semantic changes, required-field changes, digest changes, or truth-status changes require a new major contract version.
- A released schema, example, parser, serializer, digest algorithm, and consumer fixtures remain immutable for that contract version.
- Consumers must record both the contract version and immutable LineageWeave package/service artifact identity. The contract version alone does not identify the reconstruction implementation.
- Model-backed runs must additionally retain the adjudicator implementation and provider/model revision outside the v1 result payload; canonical digest determinism must not be described as provider repeatability.
- Naruon and other consumers pin an immutable LineageWeave release or service artifact and verify compatibility before enabling the integration.
