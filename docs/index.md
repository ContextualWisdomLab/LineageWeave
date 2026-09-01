# LineageWeave

LineageWeave reconstructs evidence-bound lineage, project journeys, and relationship context from scattered enterprise records so people can inspect how events, claims, posts, and decisions relate over time.

[Ask DeepWiki](https://deepwiki.com/ContextualWisdomLab/LineageWeave) · [Repository](https://github.com/ContextualWisdomLab/LineageWeave) · [Releases](https://github.com/ContextualWisdomLab/LineageWeave/releases)

## Start here

Use LineageWeave when source systems contain related records without reliable explicit cross-record links and you need a browsable, evidence-preserving view of branching histories rather than a flat search result.

The product combines deterministic lineage assembly with bounded retrieval/fusion and optional adjudication through shared ContextualWisdomLab components. It keeps source authority, authentication, tenant scope, measurement, and model-provider routing in their owning products and contracts.

## Product surfaces

- lineage reconstruction and project journeys;
- operations/dashboard views over governed records;
- evidence-aware Global Ask and related context navigation;
- authenticated API and web client over durable PostgreSQL state;
- integration with ThreadWeave, RankWeave, TEPP, contextual-orchestrator, and shared context contracts through explicit boundaries.

## Documentation

- [Repository overview and local stack](https://github.com/ContextualWisdomLab/LineageWeave/blob/main/README.md)
- [Architecture](https://github.com/ContextualWisdomLab/LineageWeave/blob/main/ARCHITECTURE.md)
- [Product requirements](product-requirements.md)
- [Product/technical gap baseline](product-technical-gap-baseline.md)
- [Architecture decisions](adr/)
- [Research notes](lineage-bi-research-notes.md)

## Status and evidence

The repository has progressed beyond its original synthetic reconstruction demo into a broader authenticated product stack, while synthetic fixtures remain important for safe examples and tests. Treat protected-main behavior, current release evidence, and repository verification as authoritative; do not infer production readiness from a documentation page or an open pull request alone.
