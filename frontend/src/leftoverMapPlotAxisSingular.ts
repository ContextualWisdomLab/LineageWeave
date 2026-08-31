/** Caption leftover-map plot axes with persisted Gabriel singular values (ADR 0324). */

import type { LeftoverMapAxis } from "./api";
import {
  formatLeftoverMapPlotAxisShare,
  LEFTOVER_MAP_PLOT_AXIS_SHARE,
} from "./leftoverMapPlotAxisShare";

export const LEFTOVER_MAP_PLOT_AXIS_SINGULAR = "leftover-map axis {axis} σ {value}";

export const LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE =
  "leftover-map axis {axis} σ {value} ({share}%)";

export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR =
  "leftover map comparison graphic leftover-map axis {axis} σ {value}";

export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE =
  "leftover map comparison graphic leftover-map axis {axis} σ {value} ({share}%)";

export const LEFTOVER_MAP_COMPARE_AXIS_SINGULAR =
  "leftover map comparison leftover axis {axis} σ {value}";

export const LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE =
  "leftover map comparison leftover axis {axis} σ {value} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_SHARE =
  "leftover map comparison leftover axis {axis} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_LABEL = "Leftover map comparison leftover axis";

export const LEFTOVER_MAP_COMPARE_AXIS_CAPTION =
  "Leftover map comparison leftover-axis share is Gabriel inertia of residual SVD axes 1 and 2. Open a leftover pair to read the post–criterion cell. The shares do not invent a leftover score.";

export type LeftoverMapPlotAxisSingular = {
  axis_index: LeftoverMapAxis["axis_index"];
  leftover_singular_value?: LeftoverMapAxis["leftover_singular_value"] | null;
};

export type LeftoverMapCompareAxisBadge = {
  key: string;
  values: { axis: number; value?: string; share?: string };
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
