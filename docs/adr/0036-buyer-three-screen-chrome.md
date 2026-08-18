# ADR 0036 — Buyer chrome is three screens: 주간 VOC, 사건 lineage, 역할·책임

**Decision status:** Accepted on this stacked PR; not protected-main truth until squash into #74
**Date:** 2026-08-18
**Depends on:** [docs/ux/buyer-ia.md](../ux/buyer-ia.md); ADR 0002; ADR 0004; ADR 0006; ADR 0007

## Context

PR #74's demo home mixed analysis-run internals, TEPP receipts, leftover-pair
sandbox, RankWeave unavailability, and next-action tutor copy with the
buyer audit path. The buyer IA names exactly three screens. 사건 lineage
still needs the original source, 5W1H slots, and source-grounded Q&A on
that same screen -- not as a fourth page or an Ask-tutor popup.

## Decision

1. Authorized buyer chrome is **주간 VOC → 사건 lineage → 역할·책임**.
2. 사건 lineage includes, as modules on that screen: original-source
   (`PostBody`, never a raw base64 dump), the Event Lineage DAG, 5W1H
   slots, and grounded Q&A. Selecting a node keeps the buyer on this
   screen and refreshes those modules.
3. 5W1H and lineage Q&A read authorized lineage + source through
   `lineageweave/five_w1h.py` and the published ontology (ADR 0004).
   A missing slot fail-closes with a next-action sentence
   (`이 사건의 누가/언제가 아직 없습니다`). 5W1H questions never
   invent prose, a theta, or a leftover number.
4. Analysis-run list/start, tutor copy of the form “X is current. Read Y
   next.”, TEPP receipts, leftover-pair sandbox, agent logs, and
   RankWeave as a home module stay off buyer chrome. Their APIs remain.

## Consequences

After `make seed`, Demo Analyst opens 주간 VOC, one VOC item, then
reads source + DAG + 5W1H + grounded Q&A and decides from R&R
Person / Organization / Team. Empty weeks, unlinked nodes, unbound
roles, and ungrounded Why/How stay honest.

## Related

Implements [docs/ux/buyer-ia.md](../ux/buyer-ia.md). Does not merge #74
to main.
