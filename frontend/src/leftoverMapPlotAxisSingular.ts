/** Caption leftover-map plot axes with persisted Gabriel singular values.
 *  ADR 0324 names leftover-map graphic-display leftover-map axis leftover-map
 *  singular values as leftoverMapPlotAxisBadge.
 *  ADR 0326 names leftover-map comparison graphic leftover-map axis leftover-map
 *  singular values as leftoverMapComparePlotAxisBadge.
 *  ADR 0327 names leftover-map graphic leftover-map axis ticks leftover-map
 *  singular values as leftoverMapPlotTickAxisBadge independently of leftover-map
 *  axis share.
 *  ADR 0328 names leftover-map comparison graphic leftover-map axis ticks leftover-map
 *  singular values as leftoverMapComparePlotTickAxisBadge independently of leftover-map
 *  axis share.
 *  ADR 0323 captions leftover-axis report badges on the grouping comparison strip
 *  as leftoverMapCompareAxisBadge, not leftoverMapComparePlotAxisBadge.
 *  ADR 0329 names leftover-map comparison leftover-axis ticks leftover-map
 *  singular values as leftoverMapCompareAxisTickBadge independently of leftover-map
 *  axis share, not leftoverMapComparePlotTickAxisBadge.
 *  ADR 0330 names leftover-map leftover-axis ticks leftover-map singular
 *  values as leftoverMapAxisTickBadge independently of leftover-map axis share,
 *  not leftoverMapCompareAxisTickBadge.
 *  ADR 0331 names leftover-map comparison graphic leftover-map axis ticks leftover-map
 *  axis share as leftoverMapComparePlotTickAxisBadge independently of leftover-map
 *  singular values.
 *  ADR 0332 names leftover-map graphic leftover-map axis ticks leftover-map
 *  axis share as leftoverMapPlotTickAxisBadge independently of leftover-map
 *  singular values.
 *  ADR 0333 names leftover-map comparison leftover-axis ticks leftover-map
 *  axis share as leftoverMapCompareAxisTickBadge independently of leftover-map
 *  singular values.
 *  ADR 0334 names leftover-map leftover-axis ticks leftover-map
 *  axis share as leftoverMapAxisTickBadge independently of leftover-map
 *  singular values.
 *  ADR 0343 names leftover-map graphic leftover-map axis origin ticks as
 *  leftoverMapPlotTickAxisBadge independently of leftover-map axis share and
 *  leftover-map singular values.
 *  ADR 0344 names leftover-map comparison graphic leftover-map axis origin ticks as
 *  leftoverMapComparePlotTickAxisBadge independently of leftover-map axis share and
 *  leftover-map singular values.
 *  ADR 0345 names leftover-map comparison leftover-axis origin ticks as
 *  leftoverMapCompareAxisTickBadge independently of leftover-map axis share and
 *  leftover-map singular values.
 *  ADR 0346 names leftover-map leftover-axis origin ticks as leftoverMapAxisTickBadge
 *  independently of leftover-map axis share and leftover-map singular values.
 *  ADR 0347 names leftover-map origin on leftover-map graphic leftover-map criterion leftover-map
 *  item coordinates as leftoverMapPlotCriterionBadge independently of leftover-map person
 *  coordinates, not leftoverMapPlotTickAxisBadge.
 *  ADR 0348 names leftover-map origin on leftover-map graphic leftover-map post leftover-map
 *  person coordinates as leftoverMapPlotPostBadge independently of leftover-map criterion leftover-map
 *  item coordinates, not leftoverMapPlotTickAxisBadge.
 */

import type { LeftoverMapAxis } from "./api";
import {
  formatLeftoverMapPlotAxisShare,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
  LEFTOVER_MAP_PLOT_AXIS_SHARE,
} from "./leftoverMapPlotAxisShare";
import {
  LEFTOVER_MAP_COMPARE_PLOT_TICK,
  LEFTOVER_MAP_PLOT_TICK,
} from "./leftoverMapPlotLayout";
import { formatSignedLeftoverValue } from "./leftoverMapUnexplained";

export const LEFTOVER_MAP_PLOT_AXIS_SINGULAR = "leftover-map axis {axis} σ {value}";

export const LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE =
  "leftover-map axis {axis} σ {value} ({share}%)";

export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR =
  "leftover map comparison graphic leftover-map axis {axis} σ {value}";

export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE =
  "leftover map comparison graphic leftover-map axis {axis} σ {value} ({share}%)";

export const LEFTOVER_MAP_PLOT_TICK_SINGULAR =
  "leftover-map axis {axis} tick {value} σ {singular}";

export const LEFTOVER_MAP_PLOT_TICK_SHARE =
  "leftover-map axis {axis} tick {value} {share}%";

export const LEFTOVER_MAP_PLOT_TICK_SINGULAR_SHARE =
  "leftover-map axis {axis} tick {value} σ {singular} {share}%";

export const LEFTOVER_MAP_PLOT_ORIGIN_TICK =
  "leftover-map axis {axis} origin tick {value}";

export const LEFTOVER_MAP_PLOT_ORIGIN_TICK_SINGULAR =
  "leftover-map axis {axis} origin tick {value} σ {singular}";

export const LEFTOVER_MAP_PLOT_ORIGIN_TICK_SHARE =
  "leftover-map axis {axis} origin tick {value} {share}%";

export const LEFTOVER_MAP_PLOT_ORIGIN_TICK_SINGULAR_SHARE =
  "leftover-map axis {axis} origin tick {value} σ {singular} {share}%";

export const LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR =
  "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular}";

export const LEFTOVER_MAP_COMPARE_PLOT_TICK_SHARE =
  "leftover map comparison graphic leftover-map axis {axis} tick {value} {share}%";

export const LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR_SHARE =
  "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular} {share}%";

export const LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK =
  "leftover map comparison graphic leftover-map axis {axis} origin tick {value}";

export const LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR =
  "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular}";

export const LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SHARE =
  "leftover map comparison graphic leftover-map axis {axis} origin tick {value} {share}%";

export const LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR_SHARE =
  "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_SINGULAR =
  "leftover map comparison leftover axis {axis} σ {value}";

export const LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE =
  "leftover map comparison leftover axis {axis} σ {value} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_SHARE =
  "leftover map comparison leftover axis {axis} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_TICK =
  "leftover map comparison leftover axis {axis} tick {value}";

export const LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR =
  "leftover map comparison leftover axis {axis} tick {value} σ {singular}";

export const LEFTOVER_MAP_COMPARE_AXIS_TICK_SHARE =
  "leftover map comparison leftover axis {axis} tick {value} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR_SHARE =
  "leftover map comparison leftover axis {axis} tick {value} σ {singular} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_ORIGIN_TICK =
  "leftover map comparison leftover axis {axis} origin tick {value}";

export const LEFTOVER_MAP_COMPARE_AXIS_ORIGIN_TICK_SINGULAR =
  "leftover map comparison leftover axis {axis} origin tick {value} σ {singular}";

export const LEFTOVER_MAP_COMPARE_AXIS_ORIGIN_TICK_SHARE =
  "leftover map comparison leftover axis {axis} origin tick {value} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_ORIGIN_TICK_SINGULAR_SHARE =
  "leftover map comparison leftover axis {axis} origin tick {value} σ {singular} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_LABEL = "Leftover map comparison leftover axis";

export const LEFTOVER_MAP_COMPARE_AXIS_CAPTION =
  "Leftover map comparison leftover-axis share is Gabriel inertia of residual SVD axes 1 and 2. Open a leftover pair to read the post–criterion cell. The shares do not invent a leftover score.";

export type LeftoverMapPlotAxisSingular = {
  axis_index: LeftoverMapAxis["axis_index"];
  leftover_singular_value?: LeftoverMapAxis["leftover_singular_value"] | null;
};

export type LeftoverMapCompareAxisBadge = {
  key: string;
  values: { axis: number; value?: string; share?: string; singular?: string };
};

export function leftoverSingularForAxis(
  axes: ReadonlyArray<LeftoverMapPlotAxisSingular> | null | undefined,
  axisIndex: number,
): number | null {
  const axis = axes?.find((candidate) => candidate.axis_index === axisIndex);
  if (
    axis == null ||
    axis.leftover_singular_value == null ||
    !Number.isFinite(axis.leftover_singular_value) ||
    axis.leftover_singular_value < 0
  ) {
    return null;
  }
  return axis.leftover_singular_value;
}

export function formatLeftoverMapPlotAxisSingular(
  leftoverSingular: number | null | undefined,
): string | null {
  if (leftoverSingular == null || !Number.isFinite(leftoverSingular) || leftoverSingular < 0) {
    return null;
  }
  return leftoverSingular.toFixed(2);
}

export function leftoverMapPlotTickIsOrigin(tickLabel: string): boolean {
  const originLabel = formatSignedLeftoverValue(0);
  return originLabel !== null && tickLabel === originLabel;
}

export function leftoverMapPlotAxisBadge(
  axisIndex: number,
  leftoverSingular: number | null | undefined,
  leftoverShare: number | null | undefined,
): LeftoverMapCompareAxisBadge | null {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const percent = formatLeftoverMapPlotAxisShare(leftoverShare);
  if (singular === null && percent === null) {
    return null;
  }
  if (singular === null && percent !== null) {
    return { key: LEFTOVER_MAP_PLOT_AXIS_SHARE, values: { axis: axisIndex, share: percent } };
  }
  if (singular !== null && percent === null) {
    return { key: LEFTOVER_MAP_PLOT_AXIS_SINGULAR, values: { axis: axisIndex, value: singular } };
  }
  return {
    key: LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE,
    values: { axis: axisIndex, value: singular as string, share: percent as string },
  };
}

export function leftoverMapCompareAxisBadge(
  axisIndex: number,
  leftoverSingular: number | null | undefined,
  leftoverShare: number | null | undefined,
): LeftoverMapCompareAxisBadge | null {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const percent = formatLeftoverMapPlotAxisShare(leftoverShare);
  if (singular === null && percent === null) {
    return null;
  }
  if (singular === null && percent !== null) {
    return { key: LEFTOVER_MAP_COMPARE_AXIS_SHARE, values: { axis: axisIndex, share: percent } };
  }
  if (singular !== null && percent === null) {
    return { key: LEFTOVER_MAP_COMPARE_AXIS_SINGULAR, values: { axis: axisIndex, value: singular } };
  }
  return {
    key: LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE,
    values: { axis: axisIndex, value: singular as string, share: percent as string },
  };
}

export function leftoverMapComparePlotAxisBadge(
  axisIndex: number,
  leftoverSingular: number | null | undefined,
  leftoverShare: number | null | undefined,
): LeftoverMapCompareAxisBadge | null {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const percent = formatLeftoverMapPlotAxisShare(leftoverShare);
  if (singular === null && percent === null) {
    return null;
  }
  if (singular === null && percent !== null) {
    return { key: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE, values: { axis: axisIndex, share: percent } };
  }
  if (singular !== null && percent === null) {
    return {
      key: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
      values: { axis: axisIndex, value: singular },
    };
  }
  return {
    key: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
    values: { axis: axisIndex, value: singular as string, share: percent as string },
  };
}

export function leftoverMapPlotTickAxisBadge(
  axisIndex: number,
  tickLabel: string,
  leftoverSingular: number | null | undefined,
  leftoverShare?: number | null,
): LeftoverMapCompareAxisBadge {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const percent = formatLeftoverMapPlotAxisShare(leftoverShare);
  const origin = leftoverMapPlotTickIsOrigin(tickLabel);
  if (singular === null && percent === null) {
    return {
      key: origin ? LEFTOVER_MAP_PLOT_ORIGIN_TICK : LEFTOVER_MAP_PLOT_TICK,
      values: { axis: axisIndex, value: tickLabel },
    };
  }
  if (singular === null && percent !== null) {
    return {
      key: origin ? LEFTOVER_MAP_PLOT_ORIGIN_TICK_SHARE : LEFTOVER_MAP_PLOT_TICK_SHARE,
      values: { axis: axisIndex, value: tickLabel, share: percent },
    };
  }
  if (singular !== null && percent === null) {
    return {
      key: origin ? LEFTOVER_MAP_PLOT_ORIGIN_TICK_SINGULAR : LEFTOVER_MAP_PLOT_TICK_SINGULAR,
      values: { axis: axisIndex, value: tickLabel, singular },
    };
  }
  return {
    key: origin ? LEFTOVER_MAP_PLOT_ORIGIN_TICK_SINGULAR_SHARE : LEFTOVER_MAP_PLOT_TICK_SINGULAR_SHARE,
    values: { axis: axisIndex, value: tickLabel, singular: singular as string, share: percent as string },
  };
}

export function leftoverMapComparePlotTickAxisBadge(
  axisIndex: number,
  tickLabel: string,
  leftoverSingular: number | null | undefined,
  leftoverShare?: number | null,
): LeftoverMapCompareAxisBadge {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const percent = formatLeftoverMapPlotAxisShare(leftoverShare);
  const origin = leftoverMapPlotTickIsOrigin(tickLabel);
  if (singular === null && percent === null) {
    return {
      key: origin ? LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK : LEFTOVER_MAP_COMPARE_PLOT_TICK,
      values: { axis: axisIndex, value: tickLabel },
    };
  }
  if (singular === null && percent !== null) {
    return {
      key: origin ? LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SHARE : LEFTOVER_MAP_COMPARE_PLOT_TICK_SHARE,
      values: { axis: axisIndex, value: tickLabel, share: percent },
    };
  }
  if (singular !== null && percent === null) {
    return {
      key: origin
        ? LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR
        : LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR,
      values: { axis: axisIndex, value: tickLabel, singular },
    };
  }
  return {
    key: origin
      ? LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR_SHARE
      : LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR_SHARE,
    values: { axis: axisIndex, value: tickLabel, singular: singular as string, share: percent as string },
  };
}

export function leftoverMapCompareAxisTickBadge(
  axisIndex: number,
  tickLabel: string,
  leftoverSingular: number | null | undefined,
  leftoverShare?: number | null,
): LeftoverMapCompareAxisBadge {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const percent = formatLeftoverMapPlotAxisShare(leftoverShare);
  const origin = leftoverMapPlotTickIsOrigin(tickLabel);
  if (singular === null && percent === null) {
    return {
      key: origin ? LEFTOVER_MAP_COMPARE_AXIS_ORIGIN_TICK : LEFTOVER_MAP_COMPARE_AXIS_TICK,
      values: { axis: axisIndex, value: tickLabel },
    };
  }
  if (singular === null && percent !== null) {
    return {
      key: origin ? LEFTOVER_MAP_COMPARE_AXIS_ORIGIN_TICK_SHARE : LEFTOVER_MAP_COMPARE_AXIS_TICK_SHARE,
      values: { axis: axisIndex, value: tickLabel, share: percent },
    };
  }
  if (singular !== null && percent === null) {
    return {
      key: origin
        ? LEFTOVER_MAP_COMPARE_AXIS_ORIGIN_TICK_SINGULAR
        : LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR,
      values: { axis: axisIndex, value: tickLabel, singular },
    };
  }
  return {
    key: origin
      ? LEFTOVER_MAP_COMPARE_AXIS_ORIGIN_TICK_SINGULAR_SHARE
      : LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR_SHARE,
    values: { axis: axisIndex, value: tickLabel, singular: singular as string, share: percent as string },
  };
}
