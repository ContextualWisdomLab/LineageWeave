/** Analyst GNB chrome: six Korean destinations, no Buyer/Cubee labels. */

export const ANALYST_GNB_ITEMS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "external", label: "외부 정보" },
  { id: "board", label: "게시판" },
  { id: "customers", label: "고객 마스터" },
  { id: "calendar", label: "달력" },
  { id: "ask", label: "Ask Agent" },
] as const;

export type AnalystGnbId = (typeof ANALYST_GNB_ITEMS)[number]["id"];

export const ANALYST_GNB_LABELS = ANALYST_GNB_ITEMS.map((item) => item.label);

export const CALENDAR_CONSUME_UNAVAILABLE = "이 범위의 일정을 아직 받을 수 없습니다";

/** Keep shared post links on the board; otherwise use the product landing page. */
export function initialWorkspaceDestination(search: string, testMode: boolean): "board" | "dashboard" {
  return testMode || new URLSearchParams(search).has("post") ? "board" : "dashboard";
}
