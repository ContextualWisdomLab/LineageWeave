"""Temporary bounded top-overlay refresh for the product/technical gap baseline."""

from pathlib import Path

path = Path("docs/product-technical-gap-baseline.md")
text = path.read_text(encoding="utf-8")
marker = "# Product & Technical Gap Baseline\n"
if not text.startswith(marker):
    raise SystemExit("unexpected baseline heading")
overlay = r'''

> Exact-head loop overlay: 2026-09-13 09:46 KST. Protected `main` remains
> `83eba56149eb802cd63642c507c324c9976ec78e`. Fresh live inventory reports
> 159 open PRs and 36 open issues. Exactly two open PRs are non-Draft, #1042
> and #1055; both are Ready only to preserve or obtain exact-head validation,
> not as merge-ready claims.
>
> Customer Master process-unit repair #1042 remains on exact
> `f23f5a567bd66113603837f86f030c3c459e69e6`. Repository Tests/Security/SAST
> are terminal GREEN and Required CodeQL/OpenCode/Noema are terminal FAILURE.
> Strix `34721720240` remains genuinely in progress on the unchanged head, so
> elapsed time alone is not used to cancel it. If that lane terminalizes while
> required failures remain, #1042 returns to Draft.
>
> Customer Master customer-hint ownership issue #1052 now has repair PR #1055
> at exact `77e7c8bd8bacb8f0ce30dd9e5ddd71c30a7632da`. Migration 0250 and Proposed
> ADR 0374 introduce normalized `source_post_customer_resolution`; hint
> corroboration captures only caller-visible eligible evidence, releases its DB
> resource before external resolution/verification, then reacquires a short
> transaction and `FOR SHARE` revalidates the exact captured sources before an
> idempotent association write. `source_post.corporate_entity_id` and
> `process_unit_id` remain authorization ownership and are never rebound to the
> resolved customer. Customer Master read models consume the normalized
> association only after source-post ABAC. A live PostgreSQL regression covers
> two private tenants sharing one synthetic hint and requires that only the
> authorized tenant's source receives the resolution association while both
> source ownership tuples remain unchanged.
>
> On #1055, fresh repository Tests `34729447666` rematerialized after Ready;
> frontend lint/test/build/Storybook is GREEN and the full PostgreSQL suite is
> still running. Draft-time central Security `34729440550`, SAST `34729440465`,
> and Required CodeQL `34729440480` remain `action_required` and did not obtain
> fresh identities on the unchanged Ready head. Canonical Ready reconciliation
> owner `.github#2045` has this canary; no no-op commit, lifecycle flip loop, or
> manual success status is used. Authenticated HTTP/E2E cross-tenant evidence,
> central security/model gates and independent current-head approval are still
> required before integration.
>
> #1054, #1047, #1046 and #1049 remain Draft. #1053 still owns Post Chat
> read-derived compute versus shared-persistence mutation authority and must not
> duplicate #1044/#1047 replay-disclosure ownership. Protected-main release
> metadata remains inconsistent (`pyproject.toml` 2.28.0 versus
> `lineageweave.__version__` 2.20.0), so protected release remains blocked.
> PR #1041 remains Draft; every older overlay below is dated evidence only.
'''
path.write_text(marker + overlay + text[len(marker):], encoding="utf-8")
