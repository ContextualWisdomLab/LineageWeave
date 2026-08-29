/** Gabriel leftover-map graphic display of persisted ``ξ_{1:2}`` / ``ζ_{1:2}``.
 *  Leftover-map axis share captions axes 1 and 2 when finite (ADR 0269).
 *  Axis ticks name persisted leftover-map coordinates (ADR 0270).
 *  Pair segments name persisted leftover-map distance ``d`` (ADR 0271),
 *  persisted leftover-map reconstruction ``R̂`` (ADR 0272), persisted
 *  leftover-map explained leftover share ``e`` (ADR 0273), and persisted
 *  leftover-map unexplained leftover share ``s`` (ADR 0274).
 */

import { formatLeftoverMapCoordinatePair } from "./leftoverMapCoordinates";
import { formatLeftoverMapExplainedShare } from "./leftoverMapExplainedShare";
import { formatLeftoverMapReconstruction } from "./leftoverMapReconstruction";
import { formatLeftoverMapUnexplainedShare } from "./leftoverMapUnexplainedShare";
import { formatSignedLeftoverValue } from "./leftoverMapUnexplained";
import type { LeftoverPair } from "./api";

export const LEFTOVER_MAP_PLOT_CAPTION =
  "Leftover map after IRT main effects. Axis ticks name persisted leftover-map coordinates. Pair segments name leftover-map distance d, leftover-map reconstruction R̂, leftover-map explained leftover share e, and leftover-map unexplained leftover share s. Click a post marker to open that post. The plot does not invent a leftover score.";

export const LEFTOVER_MAP_PLOT_POST_ACTION =
  "Open leftover-map post {title} at ξ {person}";

export const LEFTOVER_MAP_PLOT_TICK =
  "leftover-map axis {axis} tick {value}";

export const LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE =
  "leftover-map distance {label}";

export const LEFTOVER_MAP_PLOT_SEGMENT_RECONSTRUCTION =
  "leftover-map reconstruction {label}";

export const LEFTOVER_MAP_PLOT_SEGMENT_EXPLAINED_SHARE =
  "leftover-map explained leftover share {label}";

export const LEFTOVER_MAP_PLOT_SEGMENT_UNEXPLAINED_SHARE =
  "leftover-map unexplained leftover share {label}";

export const PLOT_WIDTH = 480;
export const PLOT_HEIGHT = 320;
export const PLOT_PADDING = 40;
export const PLOT_TICK_LENGTH = 6;
const UNIT_DISPLAY_SPAN = 2;
const COLLAPSED_SPAN = 1e-12;
const COINCIDENT_LABEL_OFFSET = 14;
const RECONSTRUCTION_LABEL_OFFSET = 12;

export type LeftoverMapPlottablePair = {
  pair_kind: LeftoverPair["pair_kind"];
  post_id: string;
  post_title: string;
  criterion_code: string;
  leftover_distance?: number | null;
  leftover_map_reconstruction?: number | null;
  leftover_map_explained_share?: number | null;
  leftover_map_unexplained_share?: number | null;
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
  labelX: number;
  labelY: number;
  reconstructionX: number;
  reconstructionY: number;
  explainedShareX: number;
  explainedShareY: number;
  unexplainedShareX: number;
  unexplainedShareY: number;
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

export function hasLeftoverMapPlotCoordinates(
  pair: LeftoverMapPlottablePair,
): boolean {
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
): { labelX: number; labelY: number } {
  const coincident = Math.abs(x1 - x2) < 0.01 && Math.abs(y1 - y2) < 0.01;
  return {
    labelX: (x1 + x2) / 2,
    labelY: coincident ? (y1 + y2) / 2 - COINCIDENT_LABEL_OFFSET : (y1 + y2) / 2,
  };
}

function leftoverMapStackedCaptionY(labelY: number, stackedAbove: number): number {
  return stackedAbove > 0 ? labelY + stackedAbove * RECONSTRUCTION_LABEL_OFFSET : labelY;
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
  const axes: number[] = [];
  for (const pair of plottable) {
    axes.push(
      pair.leftover_map_person_axis_1 as number,
      pair.leftover_map_person_axis_2 as number,
      pair.leftover_map_item_axis_1 as number,
      pair.leftover_map_item_axis_2 as number,
    );
  }
  // Keep the origin in view: it is the rank-0 unused-axis location, not a score.
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
      PLOT_PADDING,
    );
    const itemPos = toSvg(
      pair.leftover_map_item_axis_1 as number,
      pair.leftover_map_item_axis_2 as number,
      minAxis,
      scaleSpan,
      width,
      height,
      PLOT_PADDING,
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
    const reconstructionLabel = formatLeftoverMapReconstruction(
      pair.leftover_map_reconstruction,
    );
    const explainedShareLabel = formatLeftoverMapExplainedShare(
      pair.leftover_map_explained_share,
    );
    const unexplainedShareLabel = formatLeftoverMapUnexplainedShare(
      pair.leftover_map_unexplained_share,
    );
    const labelPosition = leftoverMapSegmentLabelPosition(
      personPos.x,
      personPos.y,
      itemPos.x,
      itemPos.y,
    );
    const reconstructionY = leftoverMapStackedCaptionY(
      labelPosition.labelY,
      distanceLabel !== null && reconstructionLabel !== null ? 1 : 0,
    );
    const explainedShareY = leftoverMapStackedCaptionY(
      labelPosition.labelY,
      (distanceLabel !== null ? 1 : 0) + (reconstructionLabel !== null ? 1 : 0),
    );
    const unexplainedShareY = leftoverMapStackedCaptionY(
      labelPosition.labelY,
      (distanceLabel !== null ? 1 : 0) +
        (reconstructionLabel !== null ? 1 : 0) +
        (explainedShareLabel !== null ? 1 : 0),
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
      reconstructionX: labelPosition.labelX,
      reconstructionY,
      explainedShareX: labelPosition.labelX,
      explainedShareY,
      unexplainedShareX: labelPosition.labelX,
      unexplainedShareY,
      ...labelPosition,
    });
  }

  const origin = toSvg(0, 0, minAxis, scaleSpan, width, height, PLOT_PADDING);
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
      PLOT_PADDING,
    ),
  };
}

export function firstPlottablePairForPost(
  pairs: LeftoverMapPlottablePair[],
  postId: string,
): LeftoverMapPlottablePair | null {
  return pairs.find((pair) => pair.post_id === postId && hasLeftoverMapPlotCoordinates(pair)) ?? null;
}
