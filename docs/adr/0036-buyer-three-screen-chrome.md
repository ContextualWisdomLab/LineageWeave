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
   5W1H, Keymen (both sides), 지식그래프 depth, 고객 그룹 tree, VOC
   근거 slide, 할 일 (issue / commitment To Do), attachments, Event
   Lineage, Ask Cubee. Those post-detail modules do not become GNB
   items. There is no calendar screen on GNB or post detail.
6. Analysis-run list/start, tutor copy, TEPP receipts, leftover-pair
   sandbox, agent logs, and RankWeave as a home module stay off buyer
   chrome.
7. Every post is submitted on the existing Valkey activity stream so
   fast-mlsirm can score it. The newspaper still reads only persisted
   ranks. Missing scores stay `이번 주 신문을 아직 받을 수 없습니다`.
   No Valkey body or queue-status UI.
8. TEPP time / multilevel / topic / KG is consumed from clues on the
   opened post and 고객 마스터. Buyer chrome does not start an
   analysis-run and does not persist a receipt. A missing clue
   fail-closes (이 글의 시간창을 아직 받을 수 없습니다). This Cloud
   slice also fail-closes after clues (`이 글의 시간·다층·토픽을 아직
   받을 수 없습니다`) and never invents a theta.
9. Same Keyman, same win-pool, and same ontology object are join-key
   labels on the Event Lineage graph only. An object not in the
   ontology fail-closes that branch (`그 객체는 온톨로지에 아직
   없습니다`). Clicking an edge stays on that graph.
10. Searxng hits appear only in Ask Cubee / grounded Q&A as `미검증
    후보`. Promote sends the buyer to 고객 마스터 to attach. Until
    attached they are not lineage parents. This Cloud slice labels the
    opened-post org as `미검증 후보` and does not search the public
    web.
11. Similar-topic scrape is a scheduler hook. Live Camoufox / article
    scrape is Remote-only. This Cloud slice fail-closes
    (`유사 토픽 글을 아직 받을 수 없습니다`) and does not plant a
    Camoufox or Searxng server or fetch the public web. Buyer chrome
    has no scrape console.
12. Do not attach Figma from this Cloud VM. Tokens and Storybook
    frames live on the operator Remote machine. ADR 0002 still
    forbids pixel-matching. A missing Figma frame is not a fourth
    GNB destination.
13. Corp / PU are Keyverse attributes on the existing OIDC login, not
    a second login form.
14. Do not copy scraped articles or ontology promotions into mail or
    calendar. Calendar, if used later, is an independent consume
    module — not this slice.

## Consequences

After `make seed`, Demo Analyst lands on 게시판, reads the scheduled
주간 신문 card (or its fail-closed empty copy), opens a post, and can
switch to 고객 마스터 or Ask Cubee. Empty slots name the next human
action.

## Related

Implements [docs/ux/buyer-ia.md](../ux/buyer-ia.md). Does not merge #74
to main.
