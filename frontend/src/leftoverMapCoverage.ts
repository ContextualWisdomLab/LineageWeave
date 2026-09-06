/** Leftover-map complete-case coverage after IRT main effects (ADR 0168 / ADR 0281). */

import type { LeftoverMapCoverage } from "./api";

export const LEFTOVER_MAP_PLOT_COVERAGE_LABEL = "Leftover-map graphic coverage";

export const LEFTOVER_MAP_PLOT_COVERAGE =
  "Leftover map used {used} of {scored} scored posts (complete-case)";

export type LeftoverMapCoverageCounts = {
  used: number;
  scored: number;
};

export function leftoverMapCoverageCounts(
  coverage: LeftoverMapCoverage | null | undefined,
): LeftoverMapCoverageCounts | null {
  if (coverage == null) {
    return null;
  }
  const used = coverage.map_post_count;
  const scored = coverage.scored_post_count;
  if (!Number.isInteger(used) || !Number.isInteger(scored)) {
    return null;
  }
  if (used < 0 || scored <= 0 || used > scored) {
    return null;
  }
  return { used, scored };
}
