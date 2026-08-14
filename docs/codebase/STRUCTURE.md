# Structure

- `lineageweave.py`: source projection, document/event graph construction, content blocks/assets, ontology/semantic persistence, reports, outbox, and HTTP adapters.
- `lineageweave_server.py`: direct PostgreSQL application, verified-actor authorization, bounded API routes, document/evidence/KG mutations, and session handling.
- `web/src/`: React product surface for the workspace, document popup, evidence drawer, KG, reports, and mutations.
- `compose/`: model-only HTTP stand-in and its container build; it is not an identity provider.
- `sql/`: reusable common-enum and analysis-table SQL references.
- `tests/`: runtime, HTTP, identity, database/queue, product-flow, and lineage contract tests.
- `docs/planning/adrs/`: product ADRs; `notes/`: research and runtime evidence; `data/` is ignored runtime output.

The source table and credentials are runtime configuration. They are not part of the repository tree or committed artifacts.

## Evidence

- `rg --files`
- `README.md`
- `ARCHITECTURE.md`
- `.gitignore`
