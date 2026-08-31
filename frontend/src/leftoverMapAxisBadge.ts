/** Caption leftover-axis report badges with persisted Gabriel singular values.
 *  ADR 0323 captions leftover-axis report badges on the grouping comparison strip
 *  with a distinct leftover map comparison leftover axis name, not this helper.
 */

import type { LeftoverMapAxis } from "./api";
import {
  formatLeftoverMapPlotAxisSingular,
  leftoverSingularForAxis,
} from "./leftoverMapPlotAxisSingular";

export const LEFTOVER_MAP_AXIS_BADGE_SHARE = "leftover axis {axis} {share}%";

export const LEFTOVER_MAP_AXIS_BADGE_SINGULAR = "leftover axis {axis} σ {value} {share}%";

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
