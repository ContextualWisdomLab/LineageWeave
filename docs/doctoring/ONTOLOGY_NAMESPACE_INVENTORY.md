# Public ontology namespace inventory

**Observed repository head:** `ef6f5a5f` (`origin/main`, 2026-08-23)
**Decision:** [ADR 0157](../adr/0157-public-ontology-namespace-identity.md)
**Issue:** [#372](https://github.com/ContextualWisdomLab/LineageWeave/issues/372)

This is a non-identifying repository inventory. It does not inspect or copy
private runtime records. An unobserved downstream store is classified as
unknown, not empty.

## Protected-main inventory

| Surface | Lowercase namespace | Repository-case namespace | Compatibility risk |
|---|---|---|---|
| Ontology source | `docs/ontology/lineageweave-kg.ttl` prefix and ontology IRI | — | Lowercase terms are the formal vocabulary. |
| Runtime resolver | `lineageweave/ontology.py` (`LW`, `LOOKUP_CODE`) | — | Every generated lookup IRI is lowercase. |
| PROV-O support profile | `docs/ontology/prov-o-support-profile.ttl` now mints its four class mappings in the canonical namespace | The imported compatibility vocabulary retains the four repository-case mappings | Public RDF can already be copied into external graphs. |
| Relational persistence | `post_project_mention.ontology_iri` accepts runtime-generated text | `provenance_resource.resource_iri` accepts arbitrary external IRIs | Existing private rows are not inspected; both columns are migration surfaces. |
| Backend serialization | Project and ontology annotations return `ontology_iri` | — | API consumers may persist emitted lowercase IRIs. |
| Frontend | Typed API fields consume `ontology_iri`; tests use representative lowercase class IRIs | — | UI links and exports must stay synchronized with the migration. |
| Tests/examples | Backend, frontend, ontology, and post-chat tests assert lowercase strings | PROV-O contract test asserts repository-case class IRIs | Tests currently preserve the split. |
| Generated publication | Not present on protected main | Not present on protected main | No Pages artifact is protected-main evidence yet. |

The tracked exact-string occurrences on protected main are:

- lowercase: `docs/ontology/lineageweave-kg.ttl`,
  `lineageweave/ontology.py`, `backend/tests/test_api.py`,
  `frontend/src/App.test.tsx`, and `tests/test_post_chat.py`;
- repository-case: `docs/ontology/namespace-compatibility.ttl` and the
  compatibility assertion in `tests/test_prov_o.py`.

## Open-PR impact inventory

Open PR content is migration impact evidence, not protected-main authority.

| PR | Exact audited head | Additional surface |
|---|---|---|
| #258 | `2e2ddd1998734d6e29dad0ba916053dd8cf27983` | SHACL and interoperability tests add lowercase consumers while retaining the repository-case support profile. |
| #349 | `40286c1f1e3d25b1e28dc6464ebd031d601fa800` | Ontology Explorer stories consume lowercase IRIs. |
| #426 | `4828b3a5e4eb180bb3cb9c5a06d1327e1003065a` | Pages generator and tests publish at the repository-case project path but deliberately do not migrate semantic identifiers. |
| #490 | `87f74c6395b7090421965359222fa29f9dd9a84d` | Knowledge-graph code, SHACL, and a semantic-projection migration add further persisted/serialized namespace surfaces. |

Re-fetch these heads before using the inventory for implementation. PR #426
contains the publication work formerly proposed by closed, unmerged PR #371.

## External-consumer classification

- **Known export-capable:** RDF ontology/support-profile files and API
  `ontology_iri` fields can leave the repository boundary.
- **Known persistence-capable:** `post_project_mention.ontology_iri` and
  `provenance_resource.resource_iri` can retain values across releases.
- **Unknown actual population:** customer databases, cached API responses,
  generated RDF bundles, and downstream graph stores are not inspectable from
  repository evidence. Migration must assume both namespace forms may exist.
- **Not evidence:** repository search cannot prove that a public IRI was never
  copied, indexed, cached, or stored elsewhere.

## Reproducible audit commands

```bash
git grep -n -E \
  'contextualwisdomlab\.github\.io/(lineageweave|LineageWeave)/ontology' \
  origin/main

gh api 'repos/ContextualWisdomLab/LineageWeave/pulls?state=open&per_page=100' \
  --paginate --jq '.[].number'
```

The second command supplies the live PR set. Each head was fetched and scanned
with `git grep` rather than inferred from PR titles.

## ADR number collision audit

At exact audited heads `87f74c63` (#490), `de7f78c5` (#355), and `2e2ddd19`
(#258), the formerly colliding work has a distinct allocation: PR #490 owns
ADR `0143`, the non-default Customer Master stack owns `0144`, PR #355 owns
`0145`, and PR #258 owns `0146`. ADRs `0150`–`0156` are also occupied by open
PRs. No protected-main or live open-PR file uses `0157`, so the namespace
decision uses ADR 0157. PR #485 now owns ADR `0158` at exact head
`216c960eaccd8afa3d018b6cdc134938bcbacb8b`; no protected-main or live open-PR
file uses `0159`, so the publication decision in this stack uses ADR 0159.
Recheck immediately before integration; neither number is a global allocator
reservation.

## Resolution (ADR 0207, 2026-08-25)

The product owner directed the opposite canonicalization: the
repository-case namespace
`https://contextualwisdomlab.github.io/LineageWeave/ontology#` is now
canonical ([ADR 0207](../adr/0207-repository-case-ontology-namespace-canonical.md),
superseding [ADR 0157](../adr/0157-public-ontology-namespace-identity.md),
resolving issue #372 and amended by [ADR 0229](../adr/0229-legacy-ontology-namespace-publication.md)).
The lowercase form is a deprecated compatibility identifier whose own path is
not served; the repository-case site publishes a dereferenceable compatibility
document with validated term-kind mappings, and stored values migrate via
`scripts/migrate_legacy_namespace.py` with its dry-run/refusal
discipline (direction reversed: lowercase rows rewrite to
repository-case). The inventory above remains the historical evidence
for why both forms were treated as externally durable.
