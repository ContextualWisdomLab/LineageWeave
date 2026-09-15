/** Project persisted leftover-map singular-value evidence into buyer-visible axis captions. */

import type { LeftoverMapAxis } from "./api";
import { formatLeftoverMapPlotAxisShare } from "./leftoverMapPlotAxisShare";

export const LEFTOVER_MAP_PLOT_AXIS_SINGULAR =
  "leftover-map axis {axis} σ {value}";

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

export type LeftoverMapPlotAxisSingular = {
  axis_index: LeftoverMapAxis["axis_index"];
  leftover_singular_value?: LeftoverMapAxis["leftover_singular_value"] | null;
};

export type LeftoverMapCompareAxisBadge = {
  template: string;
  values: Record<string, string | number>;
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

/**
 * Compose comparison-strip axis evidence without deriving one persisted
 * measurement from the other. Missing or invalid evidence is omitted
 * independently; when both are absent, no badge is rendered.
 */
export function leftoverMapCompareAxisBadge(
  axis: Pick<LeftoverMapAxis, "axis_index"> & {
    leftover_share?: LeftoverMapAxis["leftover_share"] | null;
    leftover_singular_value?: LeftoverMapAxis["leftover_singular_value"] | null;
  },
): LeftoverMapCompareAxisBadge | null {
  const singular = formatLeftoverMapPlotAxisSingular(axis.leftover_singular_value);
  const share = formatLeftoverMapPlotAxisShare(axis.leftover_share);

  if (singular === null && share === null) {
    return null;
  }
  if (singular === null && share !== null) {
    return {
      template: LEFTOVER_MAP_COMPARE_AXIS_SHARE,
      values: { axis: axis.axis_index, share },
    };
  }
  if (singular !== null && share === null) {
    return {
      template: LEFTOVER_MAP_COMPARE_AXIS_SINGULAR,
      values: { axis: axis.axis_index, value: singular },
    };
  }
  return {
    template: LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE,
    values: { axis: axis.axis_index, value: singular as string, share: share as string },
  };
}
