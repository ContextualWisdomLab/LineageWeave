# Buyer information architecture

**Status:** Implemented on this stacked PR (v2.12.5). Buyer chrome is
the three GNB destinations below. Not a grant to put bot chrome,
leftover-pair sandbox, TEPP receipts, or a generate/export control on
#74.
**Date:** 2026-08-18

Enterprise buyer chrome is exactly three GNB destinations. Nothing else
is product chrome. Weekly VOC is a **filter on 게시판**. Weekly and
monthly newspapers are **scheduled board posts**, not GNB items and not
click-to-export.

This spec names the buyer path from language already on
`feat/role-responsibility-agent-ontology`: board posts, Event Lineage,
Keymen, commitments, Orgmetra tenant grain, and Ask Cubee grounded in
the ontology (ADR 0004). It does not invent a fourth GNB item.

## Product chrome

| Buyer label | Product name already in this repo | Primary action | Fail-closed empty |
|---|---|---|---|
| 게시판 | Home board (`GET /api/posts`). Each post is an event. Weekly VOC is a list filter. Scheduled weekly/monthly newspapers appear as newspaper cards with team / PU / corporate sections. | Open one post or newspaper | 게시판에 사건이 없습니다 / 이번 주 감사할 VOC가 없습니다 / 이번 주 신문을 아직 받을 수 없습니다 |
| 고객 마스터 | Customers (Orgmetra grain), Keymen catalog, commitments calendar | Manage customers, Keymen, and commitments | 이 범위의 조직 단위를 아직 받을 수 없습니다 |
| Ask Cubee | Source-grounded Q&A (`POST /api/ask-cubee`) | Ask what happened on a lineage | 이 사건 lineage에서 근거할 수 있는 질문이 아직 없습니다 |

Buyer-facing headings use the Korean labels except **Ask Cubee**.
English names stay in file names, API fields, and ADR titles.

A grouping and a week code are how the buyer filters **which** VOC
items to audit on 게시판. They are not GNB items.

## 1. 게시판

The buyer lands here. Each post is an event. Board search binds the
query through the ontology / semantic layer (ADR 0004 /
`lineageweave/board_search.py`). A keyword-only title scan is not
search.

**Shows**

- Authorized posts, including scheduled newspaper editions.
- A **주간 VOC** checkbox filter (not a nav item).
- Newspaper cards with Corporate / PU / Team sections, like a paper.
  Importance order was consumed from persisted fast-mlsirm member
  ranks when the scheduler published the edition. Theta stays off
  the card.
- Opening any post (regular or newspaper) shows the same modules:
  원문, 5W1H, Keymen, 고객 약속, 첨부파일, 사건 lineage graph,
  Ask Cubee. Pictures stay pictures. Missing 5W1H slots fail-closed
  (이 사건의 누가/언제가 아직 없습니다).

**Scheduled newspaper**

A scheduler pre-builds each weekly / monthly edition before the buyer
arrives (`lineageweave/newspaper_edition.py`, seed/scheduler only).
The human only reads. Buyer chrome has no 생성, 실행, 내보내기, or
지금 만들기 control. A4 is print CSS on the reading screen.

Organization grain is consumed from Orgmetra (team / PU / corporate).
If Orgmetra or consumed scores are unavailable, the published edition
is an empty newspaper that names the next human action (이번 주
신문을 아직 받을 수 없습니다 / 이 범위의 조직 단위를 아직 받을 수
없습니다). Never invent ranked copy, a leftover map, RankWeave
fusion, or a theta.

**Primary action**

Open one post or newspaper.

**Not this screen**

주간 리포트 / 월간 리포트 as GNB, a generate/export button, leftover
sandbox, analysis-run list, RankWeave as a home module, or tutor copy.

## 2. 고객 마스터

Manage customers, Keymen, and commitments. Tenant identity is
Keyverse / Orgmetra when wired; this demo uses the existing OIDC
login. Do not invent an IdP or plant an org-chart kernel. Unavailable
Orgmetra fail-closes: 이 범위의 조직 단위를 아직 받을 수 없습니다.

## 3. Ask Cubee

The chat interface. Open globally or from a post. Answers only via
ontology / semantic-layer query over authorized source + lineage.
When answering about an event, the lineage graph stays on this
destination with who / what happened / chronology. Fail-closed if
ungrounded. Not a tutor menu. Not a fourth product page.

## Out of product chrome

Analysis-run internals, TEPP receipts, leftover-pair sandbox,
next-action tutor copy (“X is current. Read Y next.”), agent logs,
RankWeave as a home module, θ / IRT / CAT / FIPC numbers on buyer
chrome, and any 생성 / 실행 / 내보내기 / 지금 만들기 control.

## Design reference

Do not pixel-match or import the referenced Figma file.
[ADR 0002](../adr/0002-figma-access-boundary.md).

## Implementation (v2.12.5)

The three GNB destinations are buyer chrome on `App.tsx` (ADR 0036).
This file still must not be read as permission to put bot chrome,
leftover-pair sandbox, Rankings-unavailable home chrome, analysis-run
internals, TEPP receipts, or θ / IRT / CAT / FIPC on
`feat/role-responsibility-agent-ontology` (PR #74).
