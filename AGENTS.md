# Repository working agreement

- Keep TEPP and any contextual orchestrator integration behind HTTP; do not
  import or copy their internals into this product.
- PostgreSQL is the system of record. The source table is runtime configuration
  and must never be committed.
- React is the product surface. `web/src/App.jsx` must call the server API;
  `web/lineageweave.html` is only a compatibility redirect.
- Corp, PU, role, document, evidence, content, KG, chat, and mutation access
  must be enforced server-side from a verified Keyverse actor.
- Large or inline content stays out of graph JSON. Keep byte access behind the
  authorized document asset route.
- Cross-PU and cross-company KG relations require source document or thread
  evidence and must not be promoted to chronological transitions.
- Treat KG semantics as persisted data: classes, predicates, domain/range
  rules, node types, and evidence assertions belong in the normalized
  ontology/semantic tables. An agent may read only the post-authorization
  semantic subgraph; it must fail closed rather than infer from labels alone.
- Customer-master entities and affiliate relations require explicit
  account-to-document evidence before they are exposed through KG or analytics.
- An inferred/predicted ontology relation may be verified only through the
  authorized evidence-verification Agent: use observed internal evidence and
  optional organization-only SearXNG evidence, require the live LLM's closed
  verdict, persist the review separately, and never promote the original edge.
- If the live worker URL is absent, start the Docker Compose worker contract;
  do not substitute a recorded response or fake account.
- The Compose worker is a model proxy only. It must not import, package, or
  serve a local issuer; discovery, authorization, token, and introspection
  routes must return `404`. The retained issuer-shaped source artifact is an
  ADR-tracked audit record: do not delete, move, permission-modify, or stop a
  process in an attempt to remove it.
- Use the shared enum table `common_enum_values` and update the ADR,
  architecture, changelog, and traceability map when a boundary changes.
- Run `uv run pytest -q`, Python compilation, and `npm run build` before
  declaring the product runnable.
