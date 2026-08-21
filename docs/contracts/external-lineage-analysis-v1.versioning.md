# External lineage analysis versioning policy

- `contract_version` follows semantic versioning independently from the LineageWeave package version.
- Unknown major versions fail closed.
- Additive optional fields require a new minor contract revision and corresponding consumer fixtures.
- Vocabulary changes, field semantic changes, required-field changes, digest changes, or truth-status changes require a new major contract version.
- A released schema, example, parser, serializer, digest algorithm, and consumer fixtures remain immutable for that contract version.
- Naruon and other consumers pin an immutable LineageWeave release or service artifact and verify compatibility before enabling the integration.
