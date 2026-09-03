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
 *  ADR 0329 captions leftover-map comparison leftover-axis ticks as
 *  leftoverMapCompareAxisTickBadge, not this helper.
 *  ADR 0330 names leftover-map leftover-axis ticks leftover-map singular
 *  values as leftoverMapAxisTickBadge independently of leftover-map axis share.
 *  ADR 0331 captions leftover-map comparison graphic leftover-map axis ticks leftover-map
 *  axis share as leftoverMapComparePlotTickAxisBadge, not this helper.
 *  ADR 0332 captions leftover-map graphic leftover-map axis ticks leftover-map
 *  axis share as leftoverMapPlotTickAxisBadge, not this helper.
 *  ADR 0333 captions leftover-map comparison leftover-axis ticks leftover-map
 *  axis share as leftoverMapCompareAxisTickBadge, not this helper.
 *  ADR 0334 names leftover-map leftover-axis ticks leftover-map axis share
 *  as leftoverMapAxisTickBadge independently of leftover-map singular values.
 *  ADR 0343 captions leftover-map graphic leftover-map axis origin ticks as
 *  leftoverMapPlotTickAxisBadge, not this helper.
 *  ADR 0344 captions leftover-map comparison graphic leftover-map axis origin ticks as
 *  leftoverMapComparePlotTickAxisBadge, not this helper.
 *  ADR 0345 captions leftover-map comparison leftover-axis origin ticks as
 *  leftoverMapCompareAxisTickBadge, not this helper.
 *  ADR 0346 names leftover-map leftover-axis origin ticks as leftoverMapAxisTickBadge
 *  independently of leftover-map axis share and leftover-map singular values.
 *  ADR 0347 names leftover-map origin on leftover-map graphic leftover-map criterion leftover-map
 *  item coordinates as leftoverMapPlotCriterionBadge, not this helper.
 *  ADR 0348 names leftover-map origin on leftover-map graphic leftover-map post leftover-map
 *  person coordinates as leftoverMapPlotPostBadge, not this helper.
 *  ADR 0349 names leftover-map origin on leftover-map comparison graphic leftover-map post leftover-map
 *  person coordinates as leftoverMapComparePlotPostBadge, not this helper.
 *  ADR 0350 names leftover-map origin on leftover-map comparison graphic leftover-map criterion leftover-map
 *  item coordinates as leftoverMapComparePlotCriterionBadge, not this helper.
 *  ADR 0351 names leftover-map origin on leftover-map pair leftover-map post leftover-map
 *  person coordinates as leftoverMapListPostBadge, not this helper.
 *  ADR 0352 names leftover-map origin on leftover-map pair leftover-map criterion leftover-map
 *  item coordinates as leftoverMapListCriterionBadge, not this helper.
 *  ADR 0353 names leftover-map origin on leftover-map comparison leftover-pair leftover-map post leftover-map
 *  person coordinates as leftoverMapCompareListPostBadge, not this helper.
 *  ADR 0354 names leftover-map origin on leftover-map comparison leftover-pair leftover-map criterion leftover-map
 *  item coordinates as leftoverMapCompareListCriterionBadge, not this helper.
 *  ADR 0355 names leftover-map graphic leftover-map origin as leftoverMapPlotOriginBadge,
 *  not this helper.
 *  ADR 0356 names leftover-map comparison graphic leftover-map origin as leftoverMapComparePlotOriginBadge,
 *  not this helper.
 *  ADR 0357 names leftover-map comparison leftover-axis leftover-map origin as leftoverMapCompareAxisOriginBadge,
 *  not this helper.
 *  ADR 0358 names leftover-map leftover-axis leftover-map origin as leftoverMapAxisOriginBadge,
 *  independently of leftover-map comparison leftover-axis leftover-map origin, leftover-map comparison graphic leftover-map origin,
 *  leftover-map graphic leftover-map origin, leftover-map comparison leftover-pair leftover-map criterion leftover-map origin leftover-map
 *  item coordinates, leftover-map axis origin ticks, leftover-map axis share, and leftover-map singular values.
 *  ADR 0359 names leftover-map pair leftover-map origin as leftoverMapListOriginBadge,
 *  not this helper.
 */

import type { LeftoverMapAxis } from "./api";
import { formatLeftoverMapPlotAxisShare } from "./leftoverMapPlotAxisShare";
import type { LeftoverMapCompareAxisBadge } from "./leftoverMapPlotAxisSingular";
import {
  formatLeftoverMapPlotAxisSingular,
  leftoverMapPlotTickIsOrigin,
  leftoverSingularForAxis,
} from "./leftoverMapPlotAxisSingular";

export const LEFTOVER_MAP_AXIS_BADGE_SHARE = "leftover axis {axis} {share}%";

export const LEFTOVER_MAP_AXIS_BADGE_SINGULAR = "leftover axis {axis} σ {value} {share}%";

export const LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY = "leftover axis {axis} σ {value}";

export const LEFTOVER_MAP_AXIS_TICK = "leftover axis {axis} tick {value}";

export const LEFTOVER_MAP_AXIS_TICK_SINGULAR = "leftover axis {axis} tick {value} σ {singular}";

export const LEFTOVER_MAP_AXIS_TICK_SHARE = "leftover axis {axis} tick {value} {share}%";

export const LEFTOVER_MAP_AXIS_TICK_SINGULAR_SHARE =
  "leftover axis {axis} tick {value} σ {singular} {share}%";

export const LEFTOVER_MAP_AXIS_ORIGIN_TICK = "leftover axis {axis} origin tick {value}";

export const LEFTOVER_MAP_AXIS_ORIGIN_TICK_SINGULAR =
  "leftover axis {axis} origin tick {value} σ {singular}";

export const LEFTOVER_MAP_AXIS_ORIGIN_TICK_SHARE = "leftover axis {axis} origin tick {value} {share}%";

export const LEFTOVER_MAP_AXIS_ORIGIN_TICK_SINGULAR_SHARE =
  "leftover axis {axis} origin tick {value} σ {singular} {share}%";

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

export function leftoverMapAxisTickBadge(
  axisIndex: number,
  tickLabel: string,
  leftoverSingular: number | null | undefined,
  leftoverShare?: number | null,
): LeftoverMapCompareAxisBadge {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const percent = leftoverMapAxisBadgeShare(leftoverShare);
  const origin = leftoverMapPlotTickIsOrigin(tickLabel);
  if (singular === null && percent === null) {
    return {
      key: origin ? LEFTOVER_MAP_AXIS_ORIGIN_TICK : LEFTOVER_MAP_AXIS_TICK,
      values: { axis: axisIndex, value: tickLabel },
    };
  }
  if (singular === null && percent !== null) {
    return {
      key: origin ? LEFTOVER_MAP_AXIS_ORIGIN_TICK_SHARE : LEFTOVER_MAP_AXIS_TICK_SHARE,
      values: { axis: axisIndex, value: tickLabel, share: percent },
    };
  }
  if (singular !== null && percent === null) {
    return {
      key: origin ? LEFTOVER_MAP_AXIS_ORIGIN_TICK_SINGULAR : LEFTOVER_MAP_AXIS_TICK_SINGULAR,
      values: { axis: axisIndex, value: tickLabel, singular },
    };
  }
  return {
    key: origin
      ? LEFTOVER_MAP_AXIS_ORIGIN_TICK_SINGULAR_SHARE
      : LEFTOVER_MAP_AXIS_TICK_SINGULAR_SHARE,
    values: { axis: axisIndex, value: tickLabel, singular: singular as string, share: percent as string },
  };
}
