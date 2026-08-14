# Conventions

- Database objects use at least two words in snake_case and are guarded by `assert_common_table_name`.
- Environment-dependent values are read at runtime; secrets and source-table configuration are never committed.
- `common_enum_values` is the shared catalog for configurable visibility and entity-role values.
- Every lineage/KG relation carries evidence status and provenance. `observed`, `inferred`, and `predicted` are distinct states.
- Transition relations are reserved for observed identifier/time continuity. Topic, affiliate, role, and keyman affinity remain non-transition relations.
- HTTP adapters return explicit unavailable/rejected states. Recorded model output is not used as a production substitute.
- Mutation routes enqueue a PostgreSQL outbox event after persistence, then attempt Valkey delivery.
- React code consumes API payloads and keeps source evidence in a bounded, authorized drawer.

## Evidence

- `lineageweave.py`
- `lineageweave_server.py`
- `sql/common_enum_values.sql`
- `tests/test_identity_boundary_lock.py`
- `tests/test_postgres_and_valkey_contract.py`
