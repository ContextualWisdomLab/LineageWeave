# ADR 0375 — Summary reads cannot grant shared-catalog write authority

**Decision status:** Proposed
**Date:** 2026-09-14

## Problem

A visible summary is readable under `post_read`, but the missing-summary materialization path also admitted hierarchy/relation clients and team upserts that can mutate shared `corporate_entity` and `cataloged_team` state. Strix exact-head run `34746057545` exposed the corporate path as CWE-862; code review found the same authority leak through team upsert.

## Decision

The application boundary derives an explicit catalog-enrichment capability from `post_admin`. Without it, summary persistence forcibly substitutes Null hierarchy/relation clients and resolves teams with a parameterized read-only lookup. `allow_catalog_enrichment` defaults to `False`, so omitted capability never grants catalog writes. The operator backfill declares `False` explicitly because it already uses Null clients. `post_admin` keeps the existing verified enrichment behavior. Summary projection persistence itself remains available to `post_read`.

## Alternatives rejected

Requiring `post_admin` for the entire GET would break the read contract. Disabling summary persistence would remove useful idempotent materialization without fixing authority. A reader-local duplicate catalog would split canonical identity truth. Null clients alone are insufficient because the team upsert path would still mutate shared state.

## Evidence and follow-up

Protected `main@83eba56149eb802cd63642c507c324c9976ec78e` is the RED baseline. Focused domain tests cover reader/admin client admission and team lookup/upsert. The authenticated PostgreSQL + Keycloak + Valkey API regression remains required before acceptance, and Strix must be rerun on the repaired exact source head. #1077 remains a separate connection-lease/performance invariant.
