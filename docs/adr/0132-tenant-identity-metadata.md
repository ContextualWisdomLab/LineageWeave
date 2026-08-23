# ADR 0132: Explicit tenant identity and copyright metadata

## Status

Accepted

## Date

2026-08-22

## Figma

File ID `1Su3lDRmiZdcUs47t1QwIX`

## Context

ADR 0118 requires the header to distinguish the brand identity from the web
system name and requires the footer copyright to show an explicit year and
rights holder. The current shell stores one `brand_name` and renders the
browser's current year, so an administrator cannot provide the approved
identity metadata for a tenant.

The repository does not contain an approved CI/BI asset or usage permission.
This decision therefore adds editable metadata only; it does not invent or
ship a logo asset.

## Decision

1. Extend the existing single-row `tenant_settings` PostgreSQL table with
   `system_name`, `copyright_year`, and `copyright_holder`.
2. Keep `brand_name` as the brand identity and retain the existing
   `brandName` API field for compatibility.
3. `GET /api/settings` returns all four display values. `PATCH /api/settings`
   remains restricted to `post_admin`; omitted fields retain their current
   values so older clients can still update only `brandName`.
4. The API and database reject blank text and copyright years outside
   1900--2100. The deployment default is `LineageWeave` and `2026`; a release
   owner must replace these with the tenant's approved CI/BI and legal values
   before production release.
5. The React shell renders the configured system name in the header and the
   configured year/rights holder in the footer. It does not use the browser's
   current year.

## Consequences

- Header and footer identity fields now have a persisted, auditable source.
- Existing callers that send only `brandName` continue to work.
- The approved CI/BI image remains an explicit operational gap until the
  tenant supplies the asset and usage permission.

## References

- ADR 0118: UI·UX Standard Guide Ver.3.0 Design Overhaul
- 웹 시스템 UI·UX 표준 가이드 Ver.3.0, §§2.2.1, 2.2.3--2.2.4
