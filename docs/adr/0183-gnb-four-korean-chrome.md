# ADR 0183: Four-destination Korean analyst GNB chrome

- Status: Accepted
- Date: 2026-08-25
- Supersedes (labels only): [0037](0037-buyer-gnb-and-product-surface.md) English GNB labels
- Folds: closed unmerged #474 WorkspaceNav rename

## Context

Main still shipped `BuyerNav` with English analyst tabs (Board / Customer
master / Calendar / Ask Agent / Admin). LineageWeave is an analyst workspace,
not a storefront, so "Buyer" and "Cubee" are not product names. Calendar is
CalendarWeave / Naruon consume only (issue #336); this slice must not
add a calendar kernel. v2.17.0 wires the 달력 destination to the Naruon
projection consume helper and keeps the same fail-closed copy.

## Decision

1. Analyst Global Navigation is exactly four destinations, in this order, with
   these Korean labels regardless of locale:

   1. 게시판 (board)
   2. 고객 마스터 (customers)
   3. 달력 (calendar)
   4. Ask Agent (ask)

2. `BuyerNav` / `BuyerDestination` become `WorkspaceNav` /
   `WorkspaceDestination`. GNB CSS uses `.workspace-gnb*`. The accessible name
   is `Workspace navigation`.
3. Operator Admin remains a non-GNB destination. It is not a fifth analyst tab.
4. Weekly VOC remains a board filter. Weekly/monthly newspaper remains a
   scheduled board post. Neither is a GNB item.
5. The 달력 destination fail-closes when Naruon calendar projection consume is
   unwired or missing, with the exact copy
   `이 범위의 일정을 아직 받을 수 없습니다`. Existing advanced-review
   commitment projection is not a calendar kernel and is not this GNB surface.
   Observed Naruon occurrences stay separate from post-grounded commitments.

## Consequences

- Analyst chrome no longer shows Buyer, Cubee, Board, or Customer master.
- CalendarWeave wiring stays a later consume-only slice. This PR does not
  import naruon mailbox, ThreadWeave, or Keyverse dumps. v2.17.0 only
  activates the published calendar projection consume path.
- Historical ADRs keep the wording of their time.

## References

- ADR 0037 (original four-destination GNB)
- ADR 0038 (CalDAV consume vs internal commitments)
- Issue #336 (Naruon calendar projection)
- Closed unmerged #474 (WorkspaceNav rename)
