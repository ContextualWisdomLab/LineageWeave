# ADR 0036 — Buyer chrome is three GNB destinations: 게시판, 고객 마스터, Ask Cubee

**Decision status:** Accepted on this stacked PR; not protected-main truth until squash into #74
**Date:** 2026-08-18
**Depends on:** [docs/ux/buyer-ia.md](../ux/buyer-ia.md); ADR 0002; ADR 0003; ADR 0004

## Context

PR #74's demo home mixed analysis-run internals, TEPP receipts, leftover-pair
sandbox, RankWeave unavailability, and next-action tutor copy with the
buyer path. The buyer IA names exactly three GNB destinations. Weekly
and monthly reports are scheduled newspapers published as board posts,
not GNB items and not click-to-export.

## Decision

1. Authorized buyer GNB is **게시판 / 고객 마스터 / Ask Cubee**.
2. 주간 VOC is a filter on 게시판. 주간 리포트 and 월간 리포트 are not
   GNB items.
3. A scheduler publishes each newspaper edition as a `source_post`
   (`newspaper-week` / `newspaper-month`). Buyer chrome has no 생성,
   실행, 내보내기, or 지금 만들기 control. A4 is print CSS on the
   reading screen.
4. Importance order is consumed from persisted fast-mlsirm member
   ranks. Organization grain is consumed from Orgmetra. Missing scores
   or grain fail-close the edition (이번 주 신문을 아직 받을 수
   없습니다 / 이 범위의 조직 단위를 아직 받을 수 없습니다). Never
   invent a theta or an org-chart kernel.
5. Opening a regular post or a newspaper uses the same modules: 원문,
   5W1H, Keymen, commitments, attachments, Event Lineage, Ask Cubee.
6. Analysis-run list/start, tutor copy, TEPP receipts, leftover-pair
   sandbox, agent logs, and RankWeave as a home module stay off buyer
   chrome.

## Consequences

After `make seed`, Demo Analyst lands on 게시판, reads the scheduled
주간 신문 card (or its fail-closed empty copy), opens a post, and can
switch to 고객 마스터 or Ask Cubee. Empty slots name the next human
action.

## Related

Implements [docs/ux/buyer-ia.md](../ux/buyer-ia.md). Does not merge #74
to main.
