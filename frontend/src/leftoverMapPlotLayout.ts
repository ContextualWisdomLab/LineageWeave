/** Gabriel leftover-map graphic display of persisted `ξ/ζ` coordinates and persisted pair metrics.
 * Grouping-comparison captions through ADR 0316 reuse these persisted values; this module never derives
 * measurement truth from geometry, rank, coverage, pair counts, or neighbouring statistics.
 */

import { formatLeftoverMapCoordinatePair } from "./leftoverMapCoordinates";
import { formatLeftoverMapCrossShare } from "./leftoverMapCrossShare";
import { formatLeftoverMapExplainedShare } from "./leftoverMapExplainedShare";
import { formatLeftoverMapRank } from "./leftoverMapRank";
import { formatLeftoverMapReconstruction } from "./leftoverMapReconstruction";
import {
  formatLeftoverMapUnexplained,
  formatSignedLeftoverValue,
} from "./leftoverMapUnexplained";
import { formatLeftoverMapUnexplainedShare } from "./leftoverMapUnexplainedShare";
import { formatLeftoverMapExpected, formatLeftoverMapObserved } from "./leftoverObservedExpected";
import { formatLeftoverMapResidual } from "./leftoverResidual";
import type { LeftoverPair } from "./api";

export const LEFTOVER_MAP_PLOT_CAPTION =
  "Leftover map after IRT main effects. Axis ticks name persisted leftover-map coordinates. Pair segments name leftover-map distance d, leftover-map reconstruction R̂, leftover-map explained leftover share e, leftover-map unexplained leftover share s, leftover-map cross share x, leftover-map unexplained leftover U, leftover residual R, leftover observed Y, leftover expected E, and leftover-map rank. The plot names leftover-map complete-case coverage, leftover-map item complete-case coverage, leftover-map incomplete post coverage, and leftover-map incomplete item coverage when persisted. Click a post marker to open that post. The plot does not invent a leftover score.";

export const LEFTOVER_MAP_COMPARE_PLOT_LABEL = "Leftover map comparison graphic";

export const LEFTOVER_MAP_COMPARE_PLOT_CAPTION =
  "Leftover map comparison graphic of already-named coordinates. Click a post marker to open that post. The plot does not invent a leftover score.";

export const LEFTOVER_MAP_COMPARE_PLOT_SVG = "Leftover map comparison";

export const LEFTOVER_MAP_PLOT_POST_ACTION =
  "Open leftover-map post {title} at ξ {person}";

export const LEFTOVER_MAP_PLOT_TICK =
  "leftover-map axis {axis} tick {value}";

export const LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE =
  "leftover-map distance {label}";

export const LEFTOVER_MAP_PLOT_SEGMENT_RECONSTRUCTION =
  "leftover-map reconstruction {label}";
export { LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RECONSTRUCTION } from "./leftoverMapReconstruction";

export const LEFTOVER_MAP_PLOT_SEGMENT_EXPLAINED_SHARE =
  "leftover-map explained leftover share {label}";
export { LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPLAINED_SHARE } from "./leftoverMapExplainedShare";

export const LEFTOVER_MAP_PLOT_SEGMENT_UNEXPLAINED_SHARE =
  "leftover-map unexplained leftover share {label}";
export { LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED_SHARE } from "./leftoverMapUnexplainedShare";

export const LEFTOVER_MAP_PLOT_SEGMENT_CROSS_SHARE =
  "leftover-map cross share {label}";
export { LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_CROSS_SHARE } from "./leftoverMapCrossShare";

export const LEFTOVER_MAP_PLOT_SEGMENT_UNEXPLAINED =
  "leftover-map unexplained leftover {label}";
export { LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED } from "./leftoverMapUnexplained";

export const LEFTOVER_MAP_PLOT_SEGMENT_RESIDUAL =
  "leftover residual {label}";
export { LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL } from "./leftoverResidual";

export const LEFTOVER_MAP_PLOT_SEGMENT_OBSERVED =
  "leftover observed {label}";
export { LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_OBSERVED } from "./leftoverObservedExpected";

export const LEFTOVER_MAP_PLOT_SEGMENT_EXPECTED =
  "leftover expected {label}";

export const LEFTOVER_MAP_PLOT_SEGMENT_RANK =
  "leftover-map rank {label}";

export const PLOT_WIDTH = 480;
export const PLOT_HEIGHT = 320;
export const PLOT_PADDING = 40;
export const PLOT_TICK_LENGTH = 6;
const UNIT_DISPLAY_SPAN = 2;
const COLLAPSED_SPAN = 1e-12;
const COINCIDENT_LABEL_OFFSET = 14;
const RECONSTRUCTION_LABEL_OFFSET = 12;
const CAPTION_MIN_BASELINE = 12;
const CAPTION_EDGE_PADDING = 4;

export type LeftoverMapPlottablePair = {
  pair_kind: LeftoverPair["pair_kind"];
  post_id: string;
  post_title: string;
  criterion_code: string;
  leftover_distance?: number | null;
  leftover_map_reconstruction?: number | null;
  leftover_map_explained_share?: number | null;
  leftover_map_unexplained_share?: number | null;
  leftover_map_cross_share?: number | null;
  leftover_map_unexplained?: number | null;
  leftover_residual?: number | null;
  observed_response?: number | null;
  expected_response?: number | null;
  leftover_map_rank?: number | null;
  leftover_map_person_axis_1?: number | null;
  leftover_map_person_axis_2?: number | null;
  leftover_map_item_axis_1?: number | null;
  leftover_map_item_axis_2?: number | null;
};

export type LeftoverMapPlotPoint = {
  kind: "person" | "item";
  id: string;
  label: string;
  axis1: number;
  axis2: number;
  x: number;
  y: number;
};

export type LeftoverMapPlotSegment = {
  pairKind: "closest" | "farthest";
  postId: string;
  criterionCode: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  distanceLabel: string | null;
  reconstructionLabel: string | null;
  explainedShareLabel: string | null;
  unexplainedShareLabel: string | null;
  crossShareLabel: string | null;
  unexplainedLeftoverLabel: string | null;
  residualLabel: string | null;
  observedLabel: string | null;
  expectedLabel: string | null;
  rankLabel: string | null;
  labelX: number;
  labelY: number;
  reconstructionX: number;
  reconstructionY: number;
  explainedShareX: number;
  explainedShareY: number;
  unexplainedShareX: number;
  unexplainedShareY: number;
  crossShareX: number;
  crossShareY: number;
  unexplainedLeftoverX: number;
  unexplainedLeftoverY: number;
  residualX: number;
  residualY: number;
  observedX: number;
  observedY: number;
  expectedX: number;
  expectedY: number;
  rankX: number;
  rankY: number;
};

export type LeftoverMapPlotTick = {
  axis: 1 | 2;
  value: number;
  label: string;
  x: number;
  y: number;
  tickX2: number;
  tickY2: number;
};

export type LeftoverMapPlotLayout = {
  width: number;
  height: number;
  originX: number;
  originY: number;
  persons: LeftoverMapPlotPoint[];
  items: LeftoverMapPlotPoint[];
  segments: LeftoverMapPlotSegment[];
  ticks: LeftoverMapPlotTick[];
};

export function formatLeftoverMapDistance(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return `d ${value.toFixed(2)}`;
}

export function hasLeftoverMapPlotCoordinates(pair: LeftoverMapPlottablePair): boolean {
  return (
    formatLeftoverMapCoordinatePair(
      pair.leftover_map_person_axis_1,
      pair.leftover_map_person_axis_2,
    ) !== null &&
    formatLeftoverMapCoordinatePair(
      pair.leftover_map_item_axis_1,
      pair.leftover_map_item_axis_2,
    ) !== null
  );
}

function toSvg(
  axis1: number,
  axis2: number,
  minAxis: number,
  scaleSpan: number,
  width: number,
  height: number,
  pad: number,
): { x: number; y: number } {
  const innerW = width - pad * 2;
  const innerH = height - pad * 2;
  const pixelsPerUnit = Math.min(innerW, innerH) / scaleSpan;
  const plotWidth = scaleSpan * pixelsPerUnit;
  const plotHeight = scaleSpan * pixelsPerUnit;
  const offsetX = pad + (innerW - plotWidth) / 2;
  const offsetY = pad + (innerH - plotHeight) / 2;
  return {
    x: offsetX + (axis1 - minAxis) * pixelsPerUnit,
    y: offsetY + (minAxis + scaleSpan - axis2) * pixelsPerUnit,
  };
}

function plotPaddingForSize(width: number, height: number): number {
  return Math.min(PLOT_PADDING, Math.max(0, width) / 4, Math.max(0, height) / 4);
}

function boundedCaptionY(y: number, height: number): number {
  const maxY = Math.max(0, height - CAPTION_EDGE_PADDING);
  const minY = Math.min(CAPTION_MIN_BASELINE, maxY);
  return Math.min(Math.max(y, minY), maxY);
}

function uniqueCoordinateTicks(values: number[]): { value: number; label: string }[] {
  const byLabel = new Map<string, number>();
  for (const value of values) {
    const label = formatSignedLeftoverValue(value);
    if (label === null) {
      continue;
    }
    if (!byLabel.has(label)) {
      byLabel.set(label, value);
    }
  }
  return [...byLabel.entries()].map(([label, value]) => ({ value, label }));
}

function leftoverMapCoordinateTicks(
  axis1Values: number[],
  axis2Values: number[],
  minAxis: number,
  scaleSpan: number,
  width: number,
  height: number,
  pad: number,
): LeftoverMapPlotTick[] {
  const ticks: LeftoverMapPlotTick[] = [];
  for (const tick of uniqueCoordinateTicks(axis1Values)) {
    const atAxis = toSvg(tick.value, 0, minAxis, scaleSpan, width, height, pad);
    ticks.push({
      axis: 1,
      value: tick.value,
      label: tick.label,
      x: atAxis.x,
      y: atAxis.y,
      tickX2: atAxis.x,
      tickY2: atAxis.y + PLOT_TICK_LENGTH,
    });
  }
  for (const tick of uniqueCoordinateTicks(axis2Values)) {
    const atAxis = toSvg(0, tick.value, minAxis, scaleSpan, width, height, pad);
    ticks.push({
      axis: 2,
      value: tick.value,
      label: tick.label,
      x: atAxis.x,
      y: atAxis.y,
      tickX2: atAxis.x - PLOT_TICK_LENGTH,
      tickY2: atAxis.y,
    });
  }
  return ticks;
}

function leftoverMapSegmentLabelPosition(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  height: number,
): { labelX: number; labelY: number } {
  const coincident = Math.abs(x1 - x2) < 0.01 && Math.abs(y1 - y2) < 0.01;
  const rawLabelY = coincident ? (y1 + y2) / 2 - COINCIDENT_LABEL_OFFSET : (y1 + y2) / 2;
  return {
    labelX: (x1 + x2) / 2,
    labelY: boundedCaptionY(rawLabelY, height),
  };
}

function leftoverMapStackedCaptionY(
  labelY: number,
  stackedAbove: number,
  height: number,
): number {
  const stackedY = stackedAbove > 0 ? labelY + stackedAbove * RECONSTRUCTION_LABEL_OFFSET : labelY;
  return boundedCaptionY(stackedY, height);
}

export function layoutLeftoverMapPlot(
  pairs: LeftoverMapPlottablePair[],
  criterionLabel: (criterionCode: string) => string,
  size?: { width?: number; height?: number },
): LeftoverMapPlotLayout | null {
  const plottable = pairs.filter(hasLeftoverMapPlotCoordinates);
  if (plottable.length === 0) {
    return null;
  }

  const width = size?.width ?? PLOT_WIDTH;
  const height = size?.height ?? PLOT_HEIGHT;
  const plotPadding = plotPaddingForSize(width, height);
  const axes: number[] = [];
  for (const pair of plottable) {
    axes.push(
      pair.leftover_map_person_axis_1 as number,
      pair.leftover_map_person_axis_2 as number,
      pair.leftover_map_item_axis_1 as number,
      pair.leftover_map_item_axis_2 as number,
    );
  }
  const minObserved = Math.min(...axes, 0);
  const maxObserved = Math.max(...axes, 0);
  const observedSpan = maxObserved - minObserved;
  const scaleSpan = observedSpan < COLLAPSED_SPAN ? UNIT_DISPLAY_SPAN : observedSpan;
  const minAxis = observedSpan < COLLAPSED_SPAN ? -1 : minObserved;

  const persons = new Map<string, LeftoverMapPlotPoint>();
  const items = new Map<string, LeftoverMapPlotPoint>();
  const segments: LeftoverMapPlotSegment[] = [];
  const axis1Values = [0];
  const axis2Values = [0];

  for (const pair of plottable) {
    const personPos = toSvg(
      pair.leftover_map_person_axis_1 as number,
      pair.leftover_map_person_axis_2 as number,
      minAxis,
      scaleSpan,
      width,
      height,
      plotPadding,
    );
    const itemPos = toSvg(
      pair.leftover_map_item_axis_1 as number,
      pair.leftover_map_item_axis_2 as number,
      minAxis,
      scaleSpan,
      width,
      height,
      plotPadding,
    );
    if (!persons.has(pair.post_id)) {
      persons.set(pair.post_id, {
        kind: "person",
        id: pair.post_id,
        label: pair.post_title,
        axis1: pair.leftover_map_person_axis_1 as number,
        axis2: pair.leftover_map_person_axis_2 as number,
        ...personPos,
      });
    }
    if (!items.has(pair.criterion_code)) {
      items.set(pair.criterion_code, {
        kind: "item",
        id: pair.criterion_code,
        label: criterionLabel(pair.criterion_code),
        axis1: pair.leftover_map_item_axis_1 as number,
        axis2: pair.leftover_map_item_axis_2 as number,
        ...itemPos,
      });
    }
    axis1Values.push(
      pair.leftover_map_person_axis_1 as number,
      pair.leftover_map_item_axis_1 as number,
    );
    axis2Values.push(
      pair.leftover_map_person_axis_2 as number,
      pair.leftover_map_item_axis_2 as number,
    );

    const distanceLabel = formatLeftoverMapDistance(pair.leftover_distance);
    const reconstructionLabel = formatLeftoverMapReconstruction(pair.leftover_map_reconstruction);
    const explainedShareLabel = formatLeftoverMapExplainedShare(pair.leftover_map_explained_share);
    const unexplainedShareLabel = formatLeftoverMapUnexplainedShare(pair.leftover_map_unexplained_share);
    const crossShareLabel = formatLeftoverMapCrossShare(pair.leftover_map_cross_share);
    const unexplainedLeftoverLabel = formatLeftoverMapUnexplained(pair.leftover_map_unexplained);
    const residualLabel = formatLeftoverMapResidual(pair.leftover_residual);
    const observedLabel = formatLeftoverMapObserved(pair.observed_response);
    const expectedLabel = formatLeftoverMapExpected(pair.expected_response);
    const rankLabel = formatLeftoverMapRank(pair.leftover_map_rank);
    const labelPosition = leftoverMapSegmentLabelPosition(
      personPos.x,
      personPos.y,
      itemPos.x,
      itemPos.y,
      height,
    );

    const captions = [
      distanceLabel,
      reconstructionLabel,
      explainedShareLabel,
      unexplainedShareLabel,
      crossShareLabel,
      unexplainedLeftoverLabel,
      residualLabel,
      observedLabel,
      expectedLabel,
      rankLabel,
    ];
    const stackedY = (index: number): number =>
      leftoverMapStackedCaptionY(
        labelPosition.labelY,
        captions.slice(0, index).filter((label) => label !== null).length,
        height,
      );

    segments.push({
      pairKind: pair.pair_kind === "farthest" ? "farthest" : "closest",
      postId: pair.post_id,
      criterionCode: pair.criterion_code,
      x1: personPos.x,
      y1: personPos.y,
      x2: itemPos.x,
      y2: itemPos.y,
      distanceLabel,
      reconstructionLabel,
      explainedShareLabel,
      unexplainedShareLabel,
      crossShareLabel,
      unexplainedLeftoverLabel,
      residualLabel,
      observedLabel,
      expectedLabel,
      rankLabel,
      labelX: labelPosition.labelX,
      labelY: stackedY(0),
      reconstructionX: labelPosition.labelX,
      reconstructionY: stackedY(1),
      explainedShareX: labelPosition.labelX,
      explainedShareY: stackedY(2),
      unexplainedShareX: labelPosition.labelX,
      unexplainedShareY: stackedY(3),
      crossShareX: labelPosition.labelX,
      crossShareY: stackedY(4),
      unexplainedLeftoverX: labelPosition.labelX,
      unexplainedLeftoverY: stackedY(5),
      residualX: labelPosition.labelX,
      residualY: stackedY(6),
      observedX: labelPosition.labelX,
      observedY: stackedY(7),
      expectedX: labelPosition.labelX,
      expectedY: stackedY(8),
      rankX: labelPosition.labelX,
      rankY: stackedY(9),
    });
  }

  const origin = toSvg(0, 0, minAxis, scaleSpan, width, height, plotPadding);
  return {
    width,
    height,
    originX: origin.x,
    originY: origin.y,
    persons: [...persons.values()],
    items: [...items.values()],
    segments,
    ticks: leftoverMapCoordinateTicks(
      axis1Values,
      axis2Values,
      minAxis,
      scaleSpan,
      width,
      height,
      plotPadding,
    ),
  };
}

export function firstPlottablePairForPost(
  pairs: LeftoverMapPlottablePair[],
  postId: string,
): LeftoverMapPlottablePair | null {
  return pairs.find((pair) => pair.post_id === postId && hasLeftoverMapPlotCoordinates(pair)) ?? null;
}
