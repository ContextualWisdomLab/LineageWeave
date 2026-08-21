# ADR 0120: Normalize persistent database identifiers to two-word snake_case

- Status: Accepted
- Date: 2026-08-21
- Supersedes: the single-token naming exception in ADR 0063 and the
  single-token column names inherited by the analysis/report/content slices

## Context

The product standard requires every persistent database object name to use at
least two lowercase `snake_case` words. The live schema still contains the
legacy `bookmark` relation and several single-token columns. Keeping those
names would make the database itself contradict the current product contract,
even though the surrounding application and ADRs describe a normalized model.

## Decision

Migration `0104_two_word_database_identifiers.sql` renames only persistent
database identifiers; it does not change payload semantics or public JSON
field names:

| Existing identifier | Canonical identifier |
| --- | --- |
| `bookmark` | `post_bookmark` |
| `analysis_run_status_event.retryable` | `analysis_run_status_event.is_retryable` |
| `post_content_image.caption` | `post_content_image.image_caption` |
| `post_content_image_region.caption` | `post_content_image_region.image_caption` |
| `post_content_unit_structure.confidence` | `post_content_unit_structure.structure_confidence` |
| `post_project_mention.confidence` | `post_project_mention.mention_confidence` |
| `post_summary_role.responsibility` | `post_summary_role.responsibility_text` |
| `report_item_information.information` | `report_item_information.information_value` |
| `report_item_parameter.slope` | `report_item_parameter.item_slope` |
| `tenant_settings.id` | `tenant_settings.tenant_settings_id` |

The `analysis_run_current_status` view is recreated with
`is_retryable`. Application-facing JSON continues to use established names
such as `information`, `caption`, and `responsibility`; those are translation
boundaries, not persistent database identifiers. The migration is idempotent
for fresh and already-initialized Compose volumes and has a matching rollback.

ADR 0063 remains the source of the bookmark entity's third-normal-form and
authorization decisions; this ADR changes only its table identifier.

## Consequences

- Schema audits can enforce the two-word naming rule without exceptions.
- SQL, migrations, and database integration tests must use the canonical names.
- Public API compatibility is preserved at the application serialization
  boundary.
- Historical migration files remain immutable; replay reaches the canonical
  schema through the additive rename migration.

## Verification

Acceptance requires applying the migration to a real PostgreSQL volume,
replaying it twice, checking that no public table/view/column violates the
two-word rule, and exercising bookmark, image evidence, summaries, reports,
tenant settings, and analysis-run status queries.
