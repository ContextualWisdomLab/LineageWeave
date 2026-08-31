/** Caption leftover-axis report badges with persisted Gabriel singular values.
 *  ADR 0325 names leftover-map singular values independently of leftover-map
 *  axis share (`leftover axis {axis} σ {value}` when share is omitted).
 *  ADR 0323 captions leftover-axis report badges on the grouping comparison strip
 *  with a distinct leftover map comparison leftover axis name, not this helper.
 *  ADR 0324 captions leftover-map graphic-display axes, not this helper.
 *  ADR 0326 captions leftover-map comparison graphic leftover-map axes as
 *  leftoverMapComparePlotAxisBadge, not this helper.
 *  ADR 0327 captions leftover-map graphic leftover-map axis ticks as
 *  leftoverMapPlotTickAxisBadge, not this helper.
 *  ADR 0328 captions leftover-map comparison graphic leftover-map axis ticks as
 *  leftoverMapComparePlotTickAxisBadge, not this helper.
 */

import type { LeftoverMapAxis } from "./api";
import { formatLeftoverMapPlotAxisShare } from "./leftoverMapPlotAxisShare";
import type { LeftoverMapCompareAxisBadge } from "./leftoverMapPlotAxisSingular";
import {
  formatLeftoverMapPlotAxisSingular,
  leftoverSingularForAxis,
} from "./leftoverMapPlotAxisSingular";

export const LEFTOVER_MAP_AXIS_BADGE_SHARE = "leftover axis {axis} {share}%";

export const LEFTOVER_MAP_AXIS_BADGE_SINGULAR = "leftover axis {axis} σ {value} {share}%";

export const LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY = "leftover axis {axis} σ {value}";

export function leftoverMapAxisBadgeShare(
  leftoverShare: LeftoverMapAxis["leftover_share"] | null | undefined,
): string | null {
  return formatLeftoverMapPlotAxisShare(leftoverShare);
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

export function leftoverMapAxisBadge(
  axisIndex: number,
  leftoverSingular: number | null | undefined,
  leftoverShare: number | null | undefined,
): LeftoverMapCompareAxisBadge | null {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const percent = leftoverMapAxisBadgeShare(leftoverShare);
  if (singular === null && percent === null) {
    return null;
  }
  if (singular === null && percent !== null) {
    return { key: LEFTOVER_MAP_AXIS_BADGE_SHARE, values: { axis: axisIndex, share: percent } };
  }
  if (singular !== null && percent === null) {
    return { key: LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY, values: { axis: axisIndex, value: singular } };
  }
  return {
    key: LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
    values: { axis: axisIndex, value: singular as string, share: percent as string },
  };
}
