/** Leftover-map complete-case coverage after IRT main effects (ADR 0168 / ADR 0281 / ADR 0282 / ADR 0283 / ADR 0284 / ADR 0285 / ADR 0286 / ADR 0287 / ADR 0288 / ADR 0289 / ADR 0290 / ADR 0291). */

import type { LeftoverMapCoverage } from "./api";

export const LEFTOVER_MAP_PLOT_COVERAGE_LABEL = "Leftover-map graphic coverage";

export const LEFTOVER_MAP_LIST_COVERAGE_LABEL = "Leftover map coverage";

export const LEFTOVER_MAP_COMPARE_COVERAGE_LABEL = "Leftover map comparison coverage";

export const LEFTOVER_MAP_COMPARE_ITEM_COVERAGE_LABEL = "Leftover map comparison item coverage";

export const LEFTOVER_MAP_COMPARE_INCOMPLETE_POST_LABEL = "Leftover map comparison incomplete posts";

export const LEFTOVER_MAP_PLOT_COVERAGE =
  "Leftover map used {used} of {scored} scored posts (complete-case)";

export const LEFTOVER_MAP_PLOT_ITEM_COVERAGE_LABEL = "Leftover-map graphic item coverage";

export const LEFTOVER_MAP_PLOT_ITEM_COVERAGE =
  "Leftover map used {used} of {scored} scored criteria (complete-case)";

export const LEFTOVER_MAP_LIST_ITEM_COVERAGE_LABEL = "Leftover map item coverage";

export const LEFTOVER_MAP_LIST_INCOMPLETE_POST_LABEL = "Leftover map incomplete posts";

export const LEFTOVER_MAP_LIST_INCOMPLETE_ITEM_LABEL = "Leftover map incomplete items";

export const LEFTOVER_MAP_PLOT_INCOMPLETE_POST_LABEL = "Leftover-map graphic incomplete posts";

export const LEFTOVER_MAP_PLOT_INCOMPLETE_POST =
  "Leftover map dropped {dropped} incomplete posts";

export const LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM_LABEL = "Leftover-map graphic incomplete items";

export const LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM =
  "Leftover map dropped {dropped} incomplete criteria";

export type LeftoverMapCoverageCounts = {
  used: number;
  scored: number;
};

export type LeftoverMapIncompleteCount = {
  dropped: number;
};

export type LeftoverMapIncompletePostCount = LeftoverMapIncompleteCount;

export type LeftoverMapIncompleteItemCount = LeftoverMapIncompleteCount;

function leftoverMapCompleteCaseCounts(
  used: number,
  scored: number,
): LeftoverMapCoverageCounts | null {
  if (!Number.isInteger(used) || !Number.isInteger(scored)) {
    return null;
  }
  if (used < 0 || scored <= 0 || used > scored) {
    return null;
  }
  return { used, scored };
}

function leftoverMapDroppedCount(
  dropped: number,
  used: number,
  scored: number,
): LeftoverMapIncompleteCount | null {
  if (!Number.isInteger(dropped) || dropped < 0) {
    return null;
  }
  const completeCase = leftoverMapCompleteCaseCounts(used, scored);
  if (completeCase !== null && dropped !== completeCase.scored - completeCase.used) {
    return null;
  }
  return { dropped };
}

export function leftoverMapCoverageCounts(
  coverage: LeftoverMapCoverage | null | undefined,
): LeftoverMapCoverageCounts | null {
  if (coverage == null) {
    return null;
  }
  return leftoverMapCompleteCaseCounts(coverage.map_post_count, coverage.scored_post_count);
}

export function leftoverMapItemCoverageCounts(
  coverage: LeftoverMapCoverage | null | undefined,
): LeftoverMapCoverageCounts | null {
  if (coverage == null) {
    return null;
  }
  return leftoverMapCompleteCaseCounts(coverage.map_item_count, coverage.scored_item_count);
}

export function leftoverMapIncompletePostCount(
  coverage: LeftoverMapCoverage | null | undefined,
): LeftoverMapIncompletePostCount | null {
  if (coverage == null) {
    return null;
  }
  return leftoverMapDroppedCount(
    coverage.incomplete_post_count,
    coverage.map_post_count,
    coverage.scored_post_count,
  );
}

export function leftoverMapIncompleteItemCount(
  coverage: LeftoverMapCoverage | null | undefined,
): LeftoverMapIncompleteItemCount | null {
  if (coverage == null) {
    return null;
  }
  return leftoverMapDroppedCount(
    coverage.incomplete_item_count,
    coverage.map_item_count,
    coverage.scored_item_count,
  );
}
