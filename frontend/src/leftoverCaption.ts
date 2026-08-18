import type { LeftoverPair } from "./api";

const CRITERION_SHORT_LABEL: Record<string, string> = {
  general_sentiment_positive: "constructive",
  general_sentiment_negative: "negative",
  sales_lead_specificity: "sales-lead",
};

export function criterionShortLabel(itemCode: string): string {
  return CRITERION_SHORT_LABEL[itemCode] ?? itemCode;
}

export function leftoverRowLabel(pairKind: string): string {
  return pairKind === "farthest" ? "Farthest leftover" : "Closest leftover";
}

export function leftoverBadgeText(pair: LeftoverPair): string {
  return `${leftoverRowLabel(pair.pair_kind)} · ${criterionShortLabel(pair.criterion_code)}`;
}

export function leftoverPairsForPost(
  pairs: LeftoverPair[] | undefined,
  postId: string,
): LeftoverPair[] {
  return (pairs ?? []).filter((pair) => pair.post_id === postId);
}
