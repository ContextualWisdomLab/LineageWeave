# Actual runtime evidence: PostgreSQL report rebuild

Observed on 2026-08-18 (Asia/Seoul) against the local PostgreSQL product
stack. This record intentionally contains aggregate results only; it does
not copy source titles, organization names, post IDs, or account identifiers.

## Evidence

- `POST /api/reports/process_unit/2026-W02/rebuild` returned HTTP `200`.
- The rebuild response reported `group_count=5`.
- `GET /api/reports/process_unit/2026-W02` returned HTTP `200` and two
  persisted process-unit reports.
- Both persisted reports selected `gpcm` and `fipc`, reported
  `fit_converged=true`, and contained a computed `mean_theta` field.
- The two reports covered four and nine posts respectively, with three
  selected items per report.

## Reproduction boundary

The request used a locally provisioned OIDC account and the authenticated
FastAPI route. The route reads PostgreSQL rows and persists the report
artifacts; it does not use the synthetic frontend response fixtures. A
production Keyverse issuer and a live TEPP transport remain deployment inputs
and are not substituted by this local evidence.

## Related contracts

- `docs/adr/0003-fast-mlsirm-report-integration.md`
- `docs/adr/0029-zotero-local-reproducibility.md`
- `lineageweave/period_report.py`
- `backend/app/report_ingestion.py`
