/** Caption leftover-axis report badges with persisted Gabriel singular values. */

import type { LeftoverMapAxis } from "./api";
import { formatLeftoverMapPlotAxisShare } from "./leftoverMapPlotAxisShare";
import {
  formatLeftoverMapPlotAxisSingular,
  leftoverSingularForAxis,
} from "./leftoverMapPlotAxisSingular";

export const LEFTOVER_MAP_AXIS_BADGE_SHARE = "leftover axis {axis}{share}";

export const LEFTOVER_MAP_AXIS_BADGE_SINGULAR = "leftover axis {axis} σ {value}{share}";

export const LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY = "leftover axis {axis} σ {value}";

export const LEFTOVER_MAP_AXIS_TICK_SINGULAR =
  "leftover axis {axis} tick {value} σ {singular}";

export const LEFTOVER_MAP_AXIS_TICK_SHARE =
  "leftover axis {axis} tick {value} {share}%";

export const LEFTOVER_MAP_AXIS_TICK_SINGULAR_SHARE =
  "leftover axis {axis} tick {value} σ {singular} {share}%";

export type LeftoverMapAxisBadge = {
  template: string;
  values: Record<string, string | number>;
};

/**
 * Format report-axis share as an optional suffix consumed directly by the
 * report template. Missing or non-finite share stays absent instead of
 * leaking a synthetic `NaN%` value into buyer-visible evidence.
 */
export function leftoverMapAxisBadgeShare(
  leftoverShare: LeftoverMapAxis["leftover_share"] | null | undefined,
): string {
  const share = formatLeftoverMapPlotAxisShare(leftoverShare);
  return share === null ? "" : ` ${share}%`;
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
  const share = leftoverMapAxisBadgeShare(axis.leftover_share);

  if (singular === null && share === "") {
    return null;
  }
  if (singular === null) {
    return {
      template: LEFTOVER_MAP_AXIS_BADGE_SHARE,
      values: { axis: axis.axis_index, share },
    };
  }
  if (share === "") {
    return {
      template: LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY,
      values: { axis: axis.axis_index, value: singular },
    };
  }
  return {
    template: LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
    values: { axis: axis.axis_index, value: singular, share },
  };
}

/** Compose persisted report-axis tick σ/share without deriving either field. */
export function leftoverMapAxisTickBadge(
  axisIndex: number,
  tickLabel: string,
  leftoverSingular: number | null | undefined,
  leftoverShare?: LeftoverMapAxis["leftover_share"] | null,
): LeftoverMapAxisBadge | null {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const share = formatLeftoverMapPlotAxisShare(leftoverShare);
  if (singular === null && share === null) {
    return null;
  }
  if (singular === null) {
    return {
      template: LEFTOVER_MAP_AXIS_TICK_SHARE,
      values: { axis: axisIndex, value: tickLabel, share: share as string },
    };
  }
  if (share === null) {
    return {
      template: LEFTOVER_MAP_AXIS_TICK_SINGULAR,
      values: { axis: axisIndex, value: tickLabel, singular },
    };
  }
  return {
    template: LEFTOVER_MAP_AXIS_TICK_SINGULAR_SHARE,
    values: { axis: axisIndex, value: tickLabel, singular, share },
  };
}
