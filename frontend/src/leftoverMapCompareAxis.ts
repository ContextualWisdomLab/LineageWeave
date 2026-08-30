/** Caption leftover-map axis share on the grouping comparison strip (ADR 0293). */

import type { LeftoverMapAxis } from "./api";

export const LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL = "Leftover map comparison axis share";

export const LEFTOVER_MAP_COMPARE_AXIS_SHARE = "leftover map comparison axis {axis} {share}%";

export const LEFTOVER_MAP_LIST_AXIS_SHARE = "leftover axis {axis} {share}%";

export const LEFTOVER_MAP_PLOT_AXIS_SHARE = "leftover-map axis {axis} ({share}%)";

export type LeftoverMapCompareAxisShare = {
  axis: number;
  share: string;
};

export function leftoverMapCompareAxisShare(
  axis: Pick<LeftoverMapAxis, "axis_index" | "leftover_share"> | null | undefined,
): LeftoverMapCompareAxisShare | null {
  if (axis == null) {
    return null;
  }
  if (!Number.isInteger(axis.axis_index) || axis.axis_index < 1) {
    return null;
  }
  if (axis.leftover_share == null || !Number.isFinite(axis.leftover_share)) {
    return null;
  }
  return {
    axis: axis.axis_index,
    share: (axis.leftover_share * 100).toFixed(0),
  };
}
