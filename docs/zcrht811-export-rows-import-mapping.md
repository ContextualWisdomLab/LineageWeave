# `zcrht811_export_rows` import mapping

Column mapping for importing a SAP VOC (Voice of Customer) ticket export
into `source_post` via `scripts/import_postgresql_posts.py`. Derived by
inspecting real column values in the source table -- not guessed from SAP
field-name convention alone -- and verified end to end against a throwaway
target database (imported real rows through the real importer, confirmed
`source_post` row shape, dropped the database). No row content from the
source table appears in this document or in git history; only the schema
mapping does.

## Field mapping

| `zcrht811_export_rows` column | Importer flag | Notes |
|---|---|---|
| `guid_field` | `--post-id-column` | The stable source UUID. |
| `docnosub_field` | `--record-key-column` | Human-readable document number (date-based, e.g. `YYMMDD-NNNN-NN`). |
| `title_field` | `--title-column` | |
| `voccts_field` | `--body-column` | Rich HTML VOC content. `vocctsb_field` is a secondary/backup content field, observed empty on every sampled row -- not mapped. |
| `erdat_field` + `erzet_field` | `--created-at-column` | Two separate SAP date/time columns (`ERDAT`/`ERZET` convention); combine in the source query with `(erdat_field + erzet_field)`, not mappable as a single raw column. |
| `aedat_field` + `aezet_field` | `--updated-at-column` | Same combination pattern (`AEDAT`/`AEZET`). |
| `voctp_field` | `--voc-type-column` | Values observed: `VOC`, `VOP` (also expect `VOM`/`VOCC`/`VOCO` per the target vocabulary); maps directly, no translation needed. |
| `dtsts_field` | `--detail-state-column` **and** `--draft-column` (`--exclude-draft-value W`) | See "Publication-state gating" below -- this is the one non-obvious mapping. |
| `loevm_field` | `--deleted-column` (`--exclude-deleted-value X`) | Standard SAP deletion flag (`LOEVM`). Observed on ~0.7% of rows (295 of 43,814 at time of writing). |
| `kunnr_field` | `--source-customer-code-column` | Standard SAP customer number (`KUNNR`). |
| `zgbispjtno_field` | `--source-project-code-column` | Custom Z-field; project reference number, often empty (not every VOC record names a project). |
| `pucode_field` | `--source-business-unit-column` | Duplicated by `voc_pucode` in the source table; `pucode_field` was used since it reads as the more specific/authoritative of the two. |
| `bukrs_field` | `--source-company-code-column` | Standard SAP company code (`BUKRS`). |
| `userid_field` | `--source-author-code-column` | |
| `ernam_field` | `--source-author-name-column` | |

Not mapped (no corresponding target concept, or redundant with a mapped
column): `mandt_field` (SAP client/tenant -- a single fixed value for this
export, not per-record data), `acthguid_field` (looks like a
parent/thread activity GUID; worth investigating for
`--thread-group-column` in a follow-up once its relationship to
`post_lineage_edge`-style grouping is understood -- not mapped here to
avoid guessing), `grade_field`, `inspt_field`, `duedt_field`, `vbeln_field`,
`posnr_field`, `ststs_field` (a second, coarser status code alongside
`dtsts_field`; not needed once `dtsts_field` gates publication state),
`land1_field`, `voc_pucode` (see `pucode_field` above), `admin_txt`,
`mdraft_field`/`mreg_field` (observed **always empty** across every row in
the table -- cannot serve as a draft signal; see below), `pgcode_field`,
`erdpt_field`/`erdlo_field`/`ertlo_field`/`ertcd_field`,
`aedlo_field`/`aetlo_field`/`aetcd_field`, `source_artifact_path` /
`source_artifact_sha256` (present on this table but not used by this
mapping; `scripts/import_postgresql_posts.py` has no artifact-based body
flag today -- if `voccts_field` is ever empty for a real row and the body
must be recovered from an external artifact instead, the importer would
need a new `--body-artifact-path-column`/`--body-artifact-sha256-column`
pair added before this mapping could use it -- not observed in the rows
sampled here, all of which had inline body content).

## Publication-state gating

The importer requires a `--draft-column` with at least one non-empty value
and at least one `--exclude-draft-value` (`_validate_publication_state` in
`scripts/import_postgresql_posts.py`). `mdraft_field` -- the field whose
name most directly suggests "draft" -- is empty on every row in this table
(confirmed by an aggregate `group by`, not a sample): it carries no signal
at all for this export.

`dtsts_field` does carry a real lifecycle signal. Its observed value
distribution (of ~43,814 rows):

| `dtsts_field` | Approximate share |
|---|---|
| `A` | ~94% |
| `W` | ~5% |
| `D`, `R` | remainder |

`W` lines up with this codebase's own `WRITING_SOURCE_DETAIL_STATE_CODE`
concept (`backend/app/main.py`'s `_can_use_post_for_analysis` already
excludes posts in that state from every derived feature) -- a
`source_detail_state_code` of `"w"` is exactly what a genuinely
in-progress/not-yet-finalized record should carry. Mapping `dtsts_field`
to **both** `--detail-state-column` (so the raw state is preserved in
`source_post.source_detail_state_code`) and `--draft-column` with
`--exclude-draft-value W` (so an in-progress record is gated out of the
import the same way this codebase already gates it out of every derived
feature) is the mapping that best matches what the source data actually
means, not an arbitrary reuse of one column for two purposes.

## Verified import (throwaway database only)

Ran the unmodified `scripts/import_postgresql_posts.py` against
`postgresql://<user>@<host>/<db>` `public.zcrht811_export_rows`
(10 non-deleted rows with non-empty body content, `--allow-demo-corporate-entity`
with a clearly-marked `DEMO-SAP-VERIFY-*` scope), targeting a throwaway
database created and dropped in the same session:

- 10 source rows read, 1 correctly skipped (`dtsts_field = 'W'`), 9 imported.
- All 9 imported rows had a non-empty `post_title`; 8 had a resolved
  `source_customer_code`; 4 had a resolved `source_project_code` (expected
  sparsity -- not every VOC record names a project).

No row content was written to any git-tracked location; the throwaway
database was dropped immediately after the assertion above.
