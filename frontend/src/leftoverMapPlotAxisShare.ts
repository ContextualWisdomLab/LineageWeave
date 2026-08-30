/** Caption leftover-map plot axes with persisted Gabriel inertia share. */

import type { LeftoverMapAxis } from "./api";

export const LEFTOVER_MAP_PLOT_AXIS_SHARE = "leftover-map axis {axis} ({share}%)";

export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE =
  "leftover map comparison axis {axis} ({share}%)";

export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_1 = "leftover map comparison axis 1";

export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_2 = "leftover map comparison axis 2";

export type LeftoverMapPlotAxisShare = {
  axis_index: LeftoverMapAxis["axis_index"];
  leftover_share?: LeftoverMapAxis["leftover_share"] | null;
};

export function leftoverShareForAxis(
  axes: ReadonlyArray<LeftoverMapPlotAxisShare> | null | undefined,
  axisIndex: number,
): number | null {
  const axis = axes?.find((candidate) => candidate.axis_index === axisIndex);
  if (axis == null || axis.leftover_share == null || !Number.isFinite(axis.leftover_share)) {
    return null;
  }
  return axis.leftover_share;
}

export function formatLeftoverMapPlotAxisShare(
  leftoverShare: number | null | undefined,
): string | null {
  if (leftoverShare == null || !Number.isFinite(leftoverShare)) {
    return null;
  }
  return (leftoverShare * 100).toFixed(0);
}
