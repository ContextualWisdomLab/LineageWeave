/** Stable analyst destinations paired with locale-neutral translation keys. */

export const ANALYST_GNB_ITEMS = [
  { id: "dashboard", labelKey: "Dashboard" },
  { id: "external", labelKey: "External information" },
  { id: "board", labelKey: "Board" },
  { id: "customers", labelKey: "Customer master" },
  { id: "calendar", labelKey: "Calendar" },
  { id: "ask", labelKey: "Ask Agent" },
] as const;

export type AnalystGnbId = (typeof ANALYST_GNB_ITEMS)[number]["id"];

export const ANALYST_GNB_LABELS = ANALYST_GNB_ITEMS.map((item) => item.labelKey);

export const CALENDAR_CONSUME_UNAVAILABLE = "이 범위의 일정을 아직 받을 수 없습니다";

/** Keep shared post links on the board; otherwise use the product landing page. */
export function initialWorkspaceDestination(search: string, testMode: boolean): "board" | "dashboard" {
  return testMode || new URLSearchParams(search).has("post") ? "board" : "dashboard";
}
