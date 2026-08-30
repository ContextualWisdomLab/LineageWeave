/** Leftover-map complete-case coverage after IRT main effects (ADR 0168 / ADR 0281 / ADR 0282 / ADR 0283). */

import type { LeftoverMapCoverage } from "./api";

export const LEFTOVER_MAP_PLOT_COVERAGE_LABEL = "Leftover-map graphic coverage";

export const LEFTOVER_MAP_PLOT_COVERAGE =
  "Leftover map used {used} of {scored} scored posts (complete-case)";

export const LEFTOVER_MAP_PLOT_ITEM_COVERAGE_LABEL = "Leftover-map graphic item coverage";

export const LEFTOVER_MAP_PLOT_ITEM_COVERAGE =
  "Leftover map used {used} of {scored} scored criteria (complete-case)";

export const LEFTOVER_MAP_PLOT_INCOMPLETE_POST_LABEL = "Leftover-map graphic incomplete posts";

export const LEFTOVER_MAP_PLOT_INCOMPLETE_POST =
  "Leftover map dropped {dropped} incomplete posts";

export type LeftoverMapCoverageCounts = {
  used: number;
  scored: number;
};

export type LeftoverMapIncompletePostCount = {
  dropped: number;
};

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
  const dropped = coverage.incomplete_post_count;
  if (!Number.isInteger(dropped) || dropped < 0) {
    return null;
  }
  const completeCase = leftoverMapCompleteCaseCounts(
    coverage.map_post_count,
    coverage.scored_post_count,
  );
  if (completeCase !== null && dropped !== completeCase.scored - completeCase.used) {
    return null;
  }
  return { dropped };
}
