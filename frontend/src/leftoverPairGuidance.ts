/**
 * Leftover post–criterion landing copy (ADR 0048 / 0049 / 0135).
 *
 * Closest and farthest pairs name both the post and the Post quality
 * criterion. Clicking a pair opens that post and lands on that criterion.
 */

import { t, tf } from "./i18n";

export const LEFTOVER_CRITERION_SHORT_LABEL: Record<string, string> = {
  general_sentiment_positive: "constructive",
  general_sentiment_negative: "negative",
  sales_lead_specificity: "sales-lead",
};

export function leftoverCriterionLabel(itemCode: string): string {
  return LEFTOVER_CRITERION_SHORT_LABEL[itemCode] ?? itemCode;
}

export function postQualityCriterionElementId(criterionCode: string): string {
  return `post-quality-criterion-${criterionCode}`;
}

export type LeftoverPairOpen = {
  pair_kind: string;
  post_id: string;
  post_title: string;
  criterion_code: string;
};

export type LeftoverPairOpenOptions = {
  focusCriterionCode: string;
};

export function leftoverPairOpenOptions(pair: LeftoverPairOpen): LeftoverPairOpenOptions {
  return { focusCriterionCode: pair.criterion_code };
}

export function leftoverPairKindLabel(pairKind: string): string {
  return pairKind === "farthest" ? t("Farthest leftover") : t("Closest leftover");
}

export function leftoverPairTitle(pair: LeftoverPairOpen): string {
  return `${leftoverPairKindLabel(pair.pair_kind)}: ${pair.post_title} · ${leftoverCriterionLabel(pair.criterion_code)}`;
}

export function leftoverPairAriaLabel(pair: LeftoverPairOpen): string {
  return tf("Open leftover {kind} pair: {title} · {criterion}", {
    kind: pair.pair_kind,
    title: pair.post_title,
    criterion: leftoverCriterionLabel(pair.criterion_code),
  });
}

export function leftoverPairNextAction(pair: LeftoverPairOpen): string {
  return `Open ${pair.post_title}, then read Post quality criterion ${leftoverCriterionLabel(pair.criterion_code)}.`;
}
