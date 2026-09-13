"""Prepend the current exact-head stabilization overlay to the gap baseline."""

from pathlib import Path

path = Path("docs/product-technical-gap-baseline.md")
text = path.read_text(encoding="utf-8")
heading = "# Product & Technical Gap Baseline\n"
if not text.startswith(heading):
    raise SystemExit("unexpected baseline heading")

overlay = '''

> Exact-head loop overlay: 2026-09-13 10:14 KST. Protected `main` remains
> `83eba56149eb802cd63642c507c324c9976ec78e`, protected with a valid verified
> commit signature. Fresh non-Draft inventory contains exactly #1042 and #1055;
> both are validation admissions only, not merge-ready claims.
>
> Customer Master process-unit repair #1042 remains at exact
> `f23f5a567bd66113603837f86f030c3c459e69e6`. Repository Tests/Security/SAST
> are terminal GREEN while Required CodeQL/OpenCode/Noema are terminal FAILURE.
> Strix `34721720240` is still genuinely in progress on the unchanged head, so
> elapsed time alone is not used to cancel it. If that lane terminalizes while
> authoritative failures remain, #1042 returns to Draft.
>
> Customer-hint ownership issue #1052 / PR #1055 advanced after review to exact
> `e11ff8698f20afc4ac628a6a86611ad1348c3fcb`. Migration 0250 and Proposed ADR
> 0374 keep `source_post.corporate_entity_id` / `process_unit_id` as access
> ownership and persist resolved customer identity in
> `source_post_customer_resolution`. Request identity is whitespace-normalized
> for matching and corroboration while the association preserves the actual raw
> `source_post.source_customer_code`. External resolution still runs with the DB
> resource released; a short persistence transaction then revalidates and
> `FOR SHARE` locks the exact captured source set before writing the association.
> Customer Master now selects resolved id/name/status/evidence coherently from one
> deterministic newest resolution row rather than independent aggregate maxima.
> The bearer + PostgreSQL regression also excludes foreign same-hint evidence,
> preserves source ownership and raw spaced hints, rejects blank HTTP hints, and
> checks coherent newest-resolution metadata. The four validated CodeRabbit
> findings are repaired and their outdated threads resolved.
>
> #1055 was marked Ready on the unchanged exact head only to admit fresh
> validation. Repository Tests `34730379137` rematerialized; frontend
> lint/test/build/Storybook is GREEN and the PostgreSQL job is still active.
> Draft-time Security `34730262196`, SAST `34730262117`, and Required CodeQL
> `34730262172` are `action_required`; no fresh central Security/SAST/Required
> CodeQL/OpenCode/Noema/Strix identity appeared at the first Ready reconciliation
> read. Canonical owner `.github#2045` now carries this unchanged-head canary.
> Do not use a no-op commit, Draft/Ready oscillation, or synthetic status to
> manufacture promotion evidence.
>
> #1054, #1047, #1046 and #1049 remain Draft. Protected-main release metadata
> remains inconsistent (`pyproject.toml` 2.28.0 versus
> `lineageweave.__version__` 2.20.0), so release remains blocked. PR #1041 stays
> Draft; every older overlay below is dated evidence only.
'''

path.write_text(heading + overlay + text[len(heading):], encoding="utf-8")
