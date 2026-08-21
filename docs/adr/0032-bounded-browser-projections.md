# ADR 0032: Bound browser landing projections

- Status: Accepted
- Date: 2026-08-18

## Context

The source corpus can contain tens of thousands of authorized posts. Returning
and rendering every post and every lineage node in the initial React view
blocks the browser before a user can open an item.

## Decision

`GET /api/posts` returns a bounded page, defaulting to 50 rows and accepting a
validated `limit`/`offset`. `GET /api/lineage` returns the newest 500 visible
nodes by default and marks the response `truncated` when more nodes exist.
The post list offers an explicit Load more action. A post popup and its
post-specific lineage endpoints remain the complete-detail path.

The SQL projection applies the same public-or-affiliated-corporate ABAC rule
before pagination, and the graph projection filters edges to the returned node
set. No private row is made visible by the bound.

## Consequences

- Initial login remains usable on large real corpora.
- The landing graph is a navigational projection, not a claim that the entire
  corpus is visible in one SVG.
- A future cursor or search endpoint can replace offset pagination without
  changing the authorization contract.

## Evidence

- `backend/app/main.py`
- `backend/app/lineage_ingestion.py`
- `frontend/src/App.tsx`
- `backend/tests/test_api.py`
