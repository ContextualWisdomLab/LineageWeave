/** Caption leftover-axis report badges with persisted Gabriel singular values. */

import type { LeftoverMapAxis } from "./api";
import { formatLeftoverMapPlotAxisShare } from "./leftoverMapPlotAxisShare";
import {
  formatLeftoverMapPlotAxisSingular,
  leftoverSingularForAxis,
} from "./leftoverMapPlotAxisSingular";

export const LEFTOVER_MAP_AXIS_BADGE_SHARE = "leftover axis {axis} {share}%";

export const LEFTOVER_MAP_AXIS_BADGE_SINGULAR = "leftover axis {axis} σ {value} {share}%";

export const LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY = "leftover axis {axis} σ {value}";

export type LeftoverMapAxisBadge = {
  template: string;
  values: Record<string, string | number>;
};

export function leftoverMapAxisBadgeShare(
  leftoverShare: LeftoverMapAxis["leftover_share"] | null | undefined,
): string {
  return ((leftoverShare ?? Number.NaN) * 100).toFixed(0);
}

export function leftoverMapAxisBadgeSingular(
  axis: Pick<LeftoverMapAxis, "axis_index"> & {
    leftover_singular_value?: LeftoverMapAxis["leftover_singular_value"] | null;
  },
): string | null {
  return formatLeftoverMapPlotAxisSingular(
    leftoverSingularForAxis([axis], axis.axis_index),
  );
}

/** Keep report-axis singular and share evidence independently observable. */
export function leftoverMapAxisBadge(
  axis: Pick<LeftoverMapAxis, "axis_index"> & {
    leftover_share?: LeftoverMapAxis["leftover_share"] | null;
    leftover_singular_value?: LeftoverMapAxis["leftover_singular_value"] | null;
  },
): LeftoverMapAxisBadge | null {
  const singular = leftoverMapAxisBadgeSingular(axis);
  const share = formatLeftoverMapPlotAxisShare(axis.leftover_share);

  if (singular === null && share === null) {
    return null;
  }
  if (singular === null && share !== null) {
    return {
      template: LEFTOVER_MAP_AXIS_BADGE_SHARE,
      values: { axis: axis.axis_index, share },
    };
  }
  if (singular !== null && share === null) {
    return {
      template: LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY,
      values: { axis: axis.axis_index, value: singular },
    };
  }
  return {
    template: LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
    values: { axis: axis.axis_index, value: singular as string, share: share as string },
  };
}
