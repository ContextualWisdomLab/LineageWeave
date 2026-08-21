# Actual runtime evidence: semantic project and evidence hints

Date: 2026-08-18 (Asia/Seoul)

This note records aggregate runtime evidence only. The smoke data was
synthetic, created outside the repository, and removed after the run.

## Runtime

- Compose services: backend, frontend, Keycloak, contextual-orchestrator,
  PostgreSQL, SearXNG, and Valkey were running.
- `GET /healthz`: HTTP 200 with `status=ok`.
- PostgreSQL schema check: `post_project_mention` existed and the report
  grouping constraint accepted `project`.

## Semantic project path

- Two synthetic posts were inserted with an empty imported project field and a
  project described only in normalized post text.
- Both `GET /api/posts/{id}/summary` calls returned HTTP 200 through
  contextual-orchestrator.
- Two project mentions were returned and two `post_project_mention` rows were
  persisted with evidence/confidence payloads.
- `POST /api/reports/project/2026-W02/rebuild`: HTTP 200.
- `GET /api/reports/project/2026-W02`: HTTP 200, aggregate `report_count=2`,
  `member_rows=5`, all returned reports `fit_converged=true`, link method
  `fipc`.
- Cleanup check: synthetic source rows remaining `0`.

The report endpoint aggregate includes pre-existing local synthetic report
rows; the semantic smoke itself contributed the two-post project membership
and was not retained as repository data.
