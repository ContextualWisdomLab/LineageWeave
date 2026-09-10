/** Caption persisted leftover-map axis share and singular values on the grouping comparison strip. */

import type { LeftoverMapAxis } from "./api";

export const LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL = "Leftover map comparison axis share";

export const LEFTOVER_MAP_COMPARE_AXIS_SHARE = "leftover map comparison axis {axis} {share}%";

export const LEFTOVER_MAP_LIST_AXIS_SHARE = "leftover axis {axis} {share}%";

export const LEFTOVER_MAP_PLOT_AXIS_SHARE = "leftover-map axis {axis} ({share}%)";

export const LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_LABEL = "Leftover map comparison axis singular";

export const LEFTOVER_MAP_COMPARE_AXIS_SINGULAR = "leftover map comparison axis {axis} σ {value}";

export const LEFTOVER_MAP_LIST_AXIS_SINGULAR = "leftover axis {axis} σ {value} {share}%";

export const LEFTOVER_MAP_PLOT_AXIS_SINGULAR = "leftover-map axis {axis} σ {value}";

export type LeftoverMapCompareAxisShare = {
  axis: number;
  share: string;
};

export type LeftoverMapCompareAxisSingular = {
  axis: number;
  value: string;
};

type LeftoverMapCompareAxisSingularInput =
  Pick<LeftoverMapAxis, "axis_index"> &
  Partial<Pick<LeftoverMapAxis, "leftover_singular_value">>;

const LARGE_FIXED_TWO_DECIMAL = new Intl.NumberFormat("en-US", {
  useGrouping: false,
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

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

/**
 * Format the canonical persisted singular value for one comparison axis.
 *
 * The persisted singular field is optional at the read boundary. This
 * deliberately does not derive a singular value from share, pair count,
 * marker count, rank, distance, or coverage. Missing/invalid persisted
 * values are omitted so the UI cannot invent psychometric output.
 */
export function leftoverMapCompareAxisSingular(
  axis: LeftoverMapCompareAxisSingularInput | null | undefined,
): LeftoverMapCompareAxisSingular | null {
  if (axis == null) {
    return null;
  }
  if (!Number.isInteger(axis.axis_index) || axis.axis_index < 1) {
    return null;
  }
  if (
    axis.leftover_singular_value == null ||
    !Number.isFinite(axis.leftover_singular_value) ||
    axis.leftover_singular_value < 0
  ) {
    return null;
  }
  const value = axis.leftover_singular_value;
  return {
    axis: axis.axis_index,
    // ECMAScript toFixed switches to exponential notation at 1e21.
    value: value >= 1e21 ? LARGE_FIXED_TWO_DECIMAL.format(value) : value.toFixed(2),
  };
}
