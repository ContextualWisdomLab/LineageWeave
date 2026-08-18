# Buyer information architecture

**Status:** Implemented on this stacked PR (v2.12.5). Buyer chrome is
the three screens below. Not a grant to put bot chrome, leftover-pair
sandbox, or TEPP receipts on #74.
**Date:** 2026-08-18

Enterprise buyer chrome is exactly three screens. Nothing else is
product chrome. Audit starts at **주간 VOC**. The next decision ends
at **역할·책임**.

This spec names the buyer path from language already on
`feat/role-responsibility-agent-ontology`: VOC (`voc_type` /
`voc-evidence`), Event Lineage (`GET /api/lineage`, the popup Event
Lineage DAG), and R&R (`roles_and_responsibilities` with Person /
Organization / Team). It does not invent a fourth home module, and it
is not permission to keep or add bot chrome on that stack.

## Product chrome

| Buyer label | Product name already in this repo | Primary action | Fail-closed empty |
|---|---|---|---|
| 주간 VOC | Weekly VOC items (posts carrying a `voc_type` label such as Voice of Customer; today's Period reports week + grouping pick is the closest existing picker) | Open one VOC item | 이번 주 감사할 VOC가 없습니다 |
| 사건 lineage | Event Lineage | Select a node | 연결된 사건이 없습니다 |
| 역할·책임 | R&R | Decide the next human action from named actors | 역할·책임이 아직 없습니다 |

Buyer-facing headings use the Korean labels. English names stay in
file names, API fields, and ADR titles.

A grouping (Corporate entity / Process unit / Thread group) and a week
code (for example `2026-W02`) are how the buyer picks **which** VOC
items to audit on 주간 VOC. They are not a fourth screen.

## 1. 주간 VOC

The buyer lands here. The job is to pick this week's events and
groupings to audit, then open one item.

**Shows**

- This week's VOC items the account is authorized to see.
- The grouping the buyer is auditing (Corporate entity, Process unit,
  or Thread group) and the week field.
- Each item's title and its `voc_type` label (Voice of Customer,
  Voice of Market, and the other closed lookup labels). Extractive VOC
  evidence (`lineageweave/voc_evidence.py`) may appear on the opened
  item: the sentence that names a classified organization, or nothing.
  A missing mention is not a fabricated quote.

**Primary action**

Open one VOC item. That open is the only path into 사건 lineage.

**Fail-closed**

- Empty week: **이번 주 감사할 VOC가 없습니다** (or the same sentence
  in the account's locale). No placeholder card, no invented item.
- Never invent a score or a theta. Weekly VOC is an audit picker, not
  a measurement surface. Mean θ, member θ, IRT cells, CAT, and FIPC
  stay off this screen even when a period-report row exists behind
  the week.

**Not this screen**

Leftover-pair sandbox rows, analysis-run list rows, Rankings-unavailable
home copy, and tutor sentences of the form “X is current. Read Y next.”

## 2. 사건 lineage

The buyer follows the branch / DAG of the VOC item just opened. This
is the Event Lineage panel (`LineageDag`, `GET /api/posts/{id}/lineage`,
`GET /api/lineage`) plus three first-class modules on the **same**
screen -- not a fourth page.

**Shows**

- **원문** — the selected node's source text. Pictures stay pictures
  (`PostBody` / `splitPostBody`); never a raw base64 dump.
- The reconstruct DAG for that item: nodes are posts, edges are
  persisted lineage edges (`lineage_edge_specs` / `post_lineage_edge`).
- Direct versus indirect links when those links exist (today's 직접 /
  간접 badges).
- Which node is current after the buyer selects it.
- **5W1H** slots on the summary (`GET /api/posts/{id}/five-w1h`).
  Values come from authorized lineage + source through the ontology
  (ADR 0004 / `lineageweave/five_w1h.py`). A missing slot is
  fail-closed empty and names the next human action, e.g.
  이 사건의 누가/언제가 아직 없습니다. Never invent copy.
- **이 사건 lineage에 묻기** — source-grounded Q&A on this screen
  (`POST /api/posts/{id}/lineage-qa`). Questions about what happened
  on this lineage are this screen's question, not a tutor. While
  answering, the lineage graph stays on this screen. 5W1H questions
  are answered only via that ontology / semantic-layer query. If the
  query cannot ground a slot, fail-closed. This is not Ask-as-product-
  chrome and does not use next-action tutor copy.

**Primary action**

Select a node. That selection is the only path into 역할·책임 for
that node.

**Fail-closed**

- No reconstruct edges, no linked posts: **연결된 사건이 없습니다**.
  Today's English stand-ins (“No linked posts yet.”, “No reconstructed
  lineage yet.”) are the same honesty rule, not a different product.
- Never fake an edge. A missing channel is dropped and renormalized
  (`reconstruct.active_weights`); a weak pair stays below
  `DEFAULT_MIN_FUSED_SCORE` and does not become a parent. A Null
  embedding or adjudication client must not draw a placeholder branch.

**Not this screen**

A second home-wide Event Lineage module beside 주간 VOC, rebuild
admin chrome as buyer chrome, next-action tutor copy after the
current node, or Keyman / evaluation / chat panels presented as the
lineage itself.

## 3. 역할·책임

Who did what on the selected node. This is the R&R list already
derived by `lineageweave/post_summary.py` and rendered under **R&R**
with Person / Organization / Team badges
([ADR 0006](../adr/0006-role-responsibility-agent-ontology.md),
[ADR 0007](../adr/0007-team-actor-type.md)).

**Shows**

- Named actors on that node: `actor_name`, `actor_type_code`
  (`prov_person` / `prov_organization` / `prov_team`), optional
  affiliation, and the responsibility clause.
- Catalog chips that already store an id on `post_summary_role`
  ([ADR 0019](../adr/0019-role-catalog-identity.md),
  [ADR 0027](../adr/0027-role-person-catalog-identity.md)). A Person,
  Organization, or Team chip may open that actor. Do not rejoin catalog
  rows by display name.

**Primary action**

Decide the next human action from those named actors — who to call,
who owns the follow-up, which organization or team acted.

**Fail-closed**

- No derived roles: **역할·책임이 아직 없습니다**. Do not hide the
  section so emptiness looks like “not built.”
- Never invent an actor. `NullPostSummaryClient` leaves the channel
  unavailable. A missing mention, a historical same-name tie that
  leaves a role unbound, or an orchestrator that is not configured is
  empty — not a guessed person.

**Not this screen**

Keyman extraction admin, affiliate-tree walk as a home module, related-
node tutor copy, or a notepad of agent logs about how the roles were
derived.

## Audit path

```
주간 VOC  --open one VOC item-->  사건 lineage  --select a node-->  역할·책임
```

1. Buyer picks this week's grouping and opens one VOC item.
2. Buyer follows that item's Event Lineage and selects a node.
3. Buyer reads R&R on that node and decides the next human action.

There is no buyer step after 역할·책임. Returning to 주간 VOC starts
a new audit pick, not a fourth screen.

## Out of product chrome

These surfaces may exist as operator, measurement, or demo internals.
They are not buyer product chrome and must not be added as home
modules or popup frames on the three-screen path:

- Analysis-run internals (registry list, Request / start / outbox,
  cutoff SHA, digest prefixes, Pending / Running / Failed machine
  codes as home chrome).
- TEPP receipts, SHA-256, contract-version paragraphs, accepted-
  acknowledgement evidence, or any local psychometric substitute.
- Leftover-pair sandbox (closest / farthest post–criterion rows above
  a member list).
- Next-action tutor copy (“X is current. Read Y next.” and the
  seeded walk that lands Keyman, evaluation, related nodes, then
  Ask).
- Agent logs and derivation traces.
- RankWeave unavailable panel as a home module
  (“Rankings · RankWeave not available”).
- Bot notepad / sandbox chrome, including in-popup Ask-about-this-
  lineage chat as a buyer frame.
- θ, IRT, CAT, or FIPC numbers on buyer chrome — including mean θ
  chips and member θ badges on a weekly picker.

Fail-closed **empty** and **error** states on the three screens are
allowed and required. An honest empty sentence is product chrome; a
placeholder score is not.

## Design reference

Do not pixel-match or import the referenced Figma file. [ADR 0002](../adr/0002-figma-access-boundary.md):
that file's cover is confidential source-organization material, and
the file has no popup / Event Lineage frame. The popup was built from
a textual brief (Korean summary, key events, R&R, Event Lineage).
Cite ADR 0002 if a later change mentions Figma.

## Implementation (v2.12.5)

The three screens are buyer chrome on `App.tsx` (ADR 0036). 사건
lineage carries 원문, the DAG, 5W1H, and grounded Q&A on that same
screen. This file still must not be read as permission to put bot
chrome, leftover-pair sandbox, Rankings-unavailable home chrome,
analysis-run internals, TEPP receipts, or θ / IRT / CAT / FIPC on
`feat/role-responsibility-agent-ontology` (PR #74).

## Related

- [ADR 0001](../adr/0001-demo-identity-and-data-boundary.md) — synthetic
  identity and content only.
- [ADR 0002](../adr/0002-figma-access-boundary.md) — Figma access
  boundary.
- [ADR 0006](../adr/0006-role-responsibility-agent-ontology.md) /
  [ADR 0007](../adr/0007-team-actor-type.md) — R&R actor is Person,
  Organization, or Team.
- `lineageweave/voc_evidence.py` — extractive VOC excerpts; never a
  guessed quote.
- `lineageweave/post_summary.py` — Korean summary, key events, R&R;
  `NullPostSummaryClient` does not invent actors.
- `lineageweave/reconstruct.py` — Event Lineage edges; missing
  channels drop; weak pairs do not become parents.
