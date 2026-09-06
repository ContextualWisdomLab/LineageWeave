/** Leftover-map complete-case coverage after IRT main effects (ADR 0168 / ADR 0281 / ADR 0282). */

import type { LeftoverMapCoverage } from "./api";

export const LEFTOVER_MAP_PLOT_COVERAGE_LABEL = "Leftover-map graphic coverage";

export const LEFTOVER_MAP_PLOT_COVERAGE =
  "Leftover map used {used} of {scored} scored posts (complete-case)";

export const LEFTOVER_MAP_PLOT_ITEM_COVERAGE_LABEL = "Leftover-map graphic item coverage";

export const LEFTOVER_MAP_PLOT_ITEM_COVERAGE =
  "Leftover map used {used} of {scored} scored criteria (complete-case)";

export type LeftoverMapCoverageCounts = {
  used: number;
  scored: number;
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
