# LineageWeave agent notes

Read `AGENTS.md`, `ARCHITECTURE.md`, and the accepted ADR before changing the
runtime boundary. Keep source-derived identifiers and tenant-specific values
out of tracked documentation and logs. Prefer the existing Python standard
library and `psycopg` helpers over new dependencies.

The public API is intentionally document-scoped. Do not add a route that lets a
browser provide corp/PU claims or bypass the Keyverse session. Any new graph
relation needs an evidence status, source evidence ID, a KG authorization test,
and an ADR/traceability update when it changes an architectural decision.
It also needs a standards-backed semantic predicate, a normalized persistence
path, and a test that the actor-filtered chat context cannot read it outside the
authorized KG neighborhood.

For inferred or predicted relations, require `manage_lineage`, gather only
authorized evidence, and persist a separate LLM verification verdict. A verdict
is not an observed fact and must never rewrite the candidate edge's status or
temporal meaning.
