# LineageWeave

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ContextualWisdomLab/LineageWeave)

**Turn scattered timestamped records into navigable, evidence-bearing lineage.**

LineageWeave reconstructs git-branch-style lineage DAGs when source records do not contain explicit “this follows from that” links. It helps reviewers and analysts understand how records continue, branch, or remain unrelated while keeping every inferred connection tied to inspectable evidence.

```text
group A-100
  rec-001  Initial site visit
      └─ rec-002  Pricing follow-up
           ├─ rec-003  Revised quote
           └─ rec-004  Delivery question
                └─ rec-005  Delivery confirmed
  rec-006  Annual account review        ← separate root
```

The repository provides both a reusable Python reconstruction library and an authenticated API/web product stack. It does not turn inferred lineage into causal truth, replace the source systems that own the original records, or perform psychometric/statistical estimation itself.

## Why LineageWeave

Scattered operational records often contain useful continuity without durable parent/child links. Timestamp proximity alone is weak; text similarity alone is weak; a shared grouping key alone is weak. LineageWeave combines independent evidence channels, preserves uncertainty, and keeps unrelated records separate instead of forcing a match.

| Need | What LineageWeave provides |
| --- | --- |
| Follow record history | Branching Event Lineage instead of a flat timestamp list |
| Inspect why two records connect | Evidence-bearing edge and channel information |
| Explore related entities | Typed semantic/provenance neighborhoods kept distinct from lineage edges |
| Keep uncertainty honest | Missing providers and unsupported semantics remain explicit unknowns |
| Reuse the engine | A standalone Python API with injected external services |
| Operate a product surface | Authenticated REST/web stack backed by PostgreSQL and Keycloak |

The supporting [product requirements](docs/product-requirements.md) define product outcomes and non-goals. Architecture decisions remain normative for policy and implementation boundaries.

## Quick start: reconstruction library

LineageWeave requires Python 3.12 or newer in the current source tree.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

Map your records into `lineageweave.Record` and call `reconstruct()`:

```python
from lineageweave import reconstruct
from lineageweave.fixtures import sample_records

trees = reconstruct(sample_records())
for tree in trees:
    print(tree.group_key, "branch points:", tree.branch_points())
```

The package does not assume a particular source schema. External channels such as embeddings or LLM adjudication are injected explicitly; the null/default path does not require provider credentials.

## Run the authenticated product stack

For local product evaluation, the Makefile deliberately uses `$HOME/.env` as the Compose environment boundary so provider credentials stay outside the repository. Do not replace or overwrite an existing home credential file. A clean local run needs only an empty owner-readable file because the default development profile already supplies throwaway local-only service defaults:

```bash
if [ ! -e "$HOME/.env" ]; then
  install -m 600 /dev/null "$HOME/.env"
fi

make up
KEYCLOAK_ADMIN_PASSWORD=admin_dev_only make seed
make smoke
```

If your existing `$HOME/.env` overrides `KEYCLOAK_ADMIN_PASSWORD`, export that same value in the shell before `make seed` instead of using the shown development default. Optional contextual-orchestrator/provider settings also belong in the existing home environment boundary; add only the values you intend to manage and preserve unrelated existing entries.

This starts the repository-owned development stack and verifies the local identity round trip. Demo identities and seeded records are synthetic development fixtures, not production customer data or deployment evidence.

For frontend development, follow [`frontend/README.md`](frontend/README.md). Deployment and environment details belong in the operator documentation rather than this product landing page.

## How reconstruction works

A lineage edge is a governed inference, not a hidden heuristic verdict. The engine can combine available signals such as temporal evidence, grouping evidence, text similarity, embeddings, or an optional model adjudication channel. Unavailable channels can be omitted; malformed calibrated inputs fail closed rather than silently receiving guessed weights.

The product keeps two concepts separate:

- **Event Lineage** answers “which record plausibly continues which?” and forms the branching thread.
- **Semantic/provenance neighborhoods** answer “which typed people, organizations, projects, events, commitments, or governed constructs relate to this evidence?”

An inferred lineage edge is not labeled causal or authoritative without separate evidence. The current research basis and validation notes are documented in [`docs/lineage-bi-research-notes.md`](docs/lineage-bi-research-notes.md), with normative research policy in [ADR 0084](docs/adr/0084-lineage-research-grounding.md).

## Ecosystem integration

LineageWeave owns reconstruction, evidence-bearing lineage presentation, and its semantic neighborhood projection. Adjacent products retain their own authority:

| Product | Boundary |
| --- | --- |
| [ThreadWeave](https://github.com/ContextualWisdomLab/ThreadWeave) | Standard message/thread assembly reused where its published contract fits |
| [RankWeave](https://github.com/ContextualWisdomLab/RankWeave) | Retrieval/score fusion used through its owned contract |
| [TEPP](https://github.com/ContextualWisdomLab/TEPP) | Psychometric and statistical estimation; LineageWeave consumes published results rather than reimplementing the mathematics |
| [fast-mlsirm](https://github.com/ContextualWisdomLab/fast-mlsirm) | Measurement/calibration capabilities used by supported reporting paths |
| [contextual-orchestrator](https://github.com/ContextualWisdomLab/contextual-orchestrator) | Provider/model routing and LLM orchestration for optional model-backed channels |
| [Keyverse](https://github.com/ContextualWisdomLab/keyverse) | Ecosystem identity authority; local Keycloak fixtures do not become the production identity source of truth |

These integrations use explicit APIs/contracts. LineageWeave does not read another product's private tables or copy its numerical/model ownership into this repository.

## Architecture at a glance

```text
Source records / imports
         │
         ▼
┌──────────────────────────────┐
│        LineageWeave          │
├──────────────────────────────┤
│ record normalization         │
│ evidence channels            │
│ lineage reconstruction       │
│ provenance / semantic view   │
│ authorization-aware API      │
└──────────────┬───────────────┘
               │
       governed integrations
               │
     ┌─────────┼──────────┐
     ▼         ▼          ▼
 ThreadWeave RankWeave  TEPP /
                        orchestrator
```

The full product stack adds PostgreSQL persistence, authenticated application APIs, a browser client, and optional integration services around the same evidence boundary. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for bounded contexts and deployment structure.

## Security and evidence boundary

The authenticated product surface is designed so that source visibility and authorization remain part of the evidence contract:

- API access uses real bearer-token verification in the product stack;
- private evidence is not made visible merely because another visible record mentions the same person or entity;
- external model/provider credentials remain outside portable source and are injected at their owning integration boundary;
- synthetic demo accounts are explicitly local-development fixtures;
- generated semantic or lineage claims remain evidence-linked and do not become source-system truth by inference.

Threat, authorization, retention, and provenance decisions are documented in [`docs/adr/`](docs/adr/) and [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Verification

Install development dependencies and run the repository test suites:

```bash
pip install -e '.[dev]'
pytest
```

For the local product stack, use the same `$HOME/.env` boundary described above. After `make up`, make the effective local Keycloak administrator password available to the seed process, then run `make seed`, `make smoke`, and `make down`.

Hosted checks on the unchanged pull-request head remain the authority for integration. A successful local command, synthetic fixture, benchmark, or predecessor-head check is not promoted into release, deployment, customer, or production-readiness evidence.

## Documentation map

| Goal | Start here |
| --- | --- |
| Product requirements and non-goals | [`docs/product-requirements.md`](docs/product-requirements.md) |
| Architecture and responsibility boundaries | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Architecture decisions | [`docs/adr/`](docs/adr/) |
| Reconstruction research and validation | [`docs/lineage-bi-research-notes.md`](docs/lineage-bi-research-notes.md) |
| Public documentation landing | [`docs/index.html`](docs/index.html) |
| Frontend development | [`frontend/README.md`](frontend/README.md) |
| Current package/runtime metadata | [`pyproject.toml`](pyproject.toml) |

## Contributing

Keep Event Lineage distinct from ontology/KG relationships, preserve evidence and authorization boundaries, and do not move statistical/psychometric arithmetic into this repository. Public contract changes should update tests, architecture decisions, and customer/operator documentation together.

## License

LineageWeave is licensed under the [MIT License](LICENSE). Third-party dependencies and external datasets retain their own licenses and must remain compatible with ContextualWisdomLab's commercial-use policy.
