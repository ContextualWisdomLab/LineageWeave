/** Project persisted leftover-map singular-value evidence into buyer-visible axis captions. */

import type { LeftoverMapAxis } from "./api";
import {
  formatLeftoverMapPlotAxisShare,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
} from "./leftoverMapPlotAxisShare";
import { formatSignedLeftoverValue } from "./leftoverMapUnexplained";

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

export const LEFTOVER_MAP_PLOT_TICK_SINGULAR =
  "leftover-map axis {axis} tick {value} σ {singular}";

export const LEFTOVER_MAP_PLOT_TICK_SHARE =
  "leftover-map axis {axis} tick {value} {share}%";

export const LEFTOVER_MAP_PLOT_TICK_SINGULAR_SHARE =
  "leftover-map axis {axis} tick {value} σ {singular} {share}%";

export const LEFTOVER_MAP_COMPARE_PLOT_TICK =
  "leftover map comparison graphic leftover-map axis {axis} tick {value}";

export const LEFTOVER_MAP_COMPARE_PLOT_TICK_SHARE =
  "leftover map comparison graphic leftover-map axis {axis} tick {value} {share}%";

export const LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR =
  "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular}";

export const LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR_SHARE =
  "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular} {share}%";

export const LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK =
  "leftover map comparison graphic leftover-map axis {axis} origin tick {value}";

export const LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SHARE =
  "leftover map comparison graphic leftover-map axis {axis} origin tick {value} {share}%";

export const LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR =
  "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular}";

export const LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR_SHARE =
  "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR =
  "leftover map comparison leftover axis {axis} tick {value} σ {singular}";

export const LEFTOVER_MAP_COMPARE_AXIS_TICK_SHARE =
  "leftover map comparison leftover axis {axis} tick {value} {share}%";

export const LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR_SHARE =
  "leftover map comparison leftover axis {axis} tick {value} σ {singular} {share}%";

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
 * Compose comparison-graphic axis evidence without deriving one persisted
 * measurement from the other. Missing or invalid evidence is omitted
 * independently; when both are absent, no badge is rendered.
 */
export function leftoverMapComparePlotAxisBadge(
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
      template: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
      values: { axis: axis.axis_index, share },
    };
  }
  if (singular !== null && share === null) {
    return {
      template: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
      values: { axis: axis.axis_index, value: singular },
    };
  }
  return {
    template: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
    values: { axis: axis.axis_index, value: singular as string, share: share as string },
  };
}

/** Exact origin identity follows the canonical persisted-coordinate formatter only. */
export function leftoverMapPlotTickIsOrigin(tickLabel: string): boolean {
  const originLabel = formatSignedLeftoverValue(0);
  return originLabel !== null && tickLabel === originLabel;
}

/**
 * Project one comparison-graphic tick without deriving origin, share, or σ from
 * each other. Each persisted evidence field can therefore fail closed on its own.
 */
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
      template: origin ? LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK : LEFTOVER_MAP_COMPARE_PLOT_TICK,
      values: { axis: axisIndex, value: tickLabel },
    };
  }
  if (singular === null) {
    return {
      template: origin ? LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SHARE : LEFTOVER_MAP_COMPARE_PLOT_TICK_SHARE,
      values: { axis: axisIndex, value: tickLabel, share: percent as string },
    };
  }
  if (percent === null) {
    return {
      template: origin
        ? LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR
        : LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR,
      values: { axis: axisIndex, value: tickLabel, singular },
    };
  }
  return {
    template: origin
      ? LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR_SHARE
      : LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR_SHARE,
    values: { axis: axisIndex, value: tickLabel, singular, share: percent },
  };
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

/** Compose persisted report-graphic tick σ/share without deriving either field. */
export function leftoverMapPlotTickAxisBadge(
  axisIndex: number,
  tickLabel: string,
  leftoverSingular: number | null | undefined,
  leftoverShare?: LeftoverMapAxis["leftover_share"] | null,
): LeftoverMapCompareAxisBadge | null {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const share = formatLeftoverMapPlotAxisShare(leftoverShare);
  if (singular === null && share === null) {
    return null;
  }
  if (singular === null) {
    return {
      template: LEFTOVER_MAP_PLOT_TICK_SHARE,
      values: { axis: axisIndex, value: tickLabel, share: share as string },
    };
  }
  if (share === null) {
    return {
      template: LEFTOVER_MAP_PLOT_TICK_SINGULAR,
      values: { axis: axisIndex, value: tickLabel, singular },
    };
  }
  return {
    template: LEFTOVER_MAP_PLOT_TICK_SINGULAR_SHARE,
    values: { axis: axisIndex, value: tickLabel, singular, share },
  };
}

/** Compose persisted comparison-strip tick σ/share without deriving either field. */
export function leftoverMapCompareAxisTickBadge(
  axisIndex: number,
  tickLabel: string,
  leftoverSingular: number | null | undefined,
  leftoverShare?: LeftoverMapAxis["leftover_share"] | null,
): LeftoverMapCompareAxisBadge | null {
  const singular = formatLeftoverMapPlotAxisSingular(leftoverSingular);
  const share = formatLeftoverMapPlotAxisShare(leftoverShare);
  if (singular === null && share === null) {
    return null;
  }
  if (singular === null) {
    return {
      template: LEFTOVER_MAP_COMPARE_AXIS_TICK_SHARE,
      values: { axis: axisIndex, value: tickLabel, share: share as string },
    };
  }
  if (share === null) {
    return {
      template: LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR,
      values: { axis: axisIndex, value: tickLabel, singular },
    };
  }
  return {
    template: LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR_SHARE,
    values: { axis: axisIndex, value: tickLabel, singular, share },
  };
}
