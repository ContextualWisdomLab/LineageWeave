/** Gabriel leftover-map graphic display of persisted ``ξ_{1:2}`` / ``ζ_{1:2}``.
 *  Leftover-map axis share captions axes 1 and 2 when finite (ADR 0269).
 *  Leftover-map singular values caption leftover-map graphic-display axes when
 *  finite (ADR 0324).
 *  Axis ticks name persisted leftover-map coordinates (ADR 0270).
 *  Pair segments name persisted leftover-map distance ``d`` (ADR 0271),
 *  persisted leftover-map reconstruction ``R̂`` (ADR 0272), persisted
 *  leftover-map explained leftover share ``e`` (ADR 0273), persisted
 *  leftover-map unexplained leftover share ``s`` (ADR 0274), persisted
 *  leftover-map cross share ``x`` (ADR 0275), persisted leftover-map
 *  unexplained leftover ``U`` (ADR 0276), persisted leftover residual
 *  ``R`` (ADR 0277), persisted leftover observed ``Y`` (ADR 0278),
 *  persisted leftover expected ``E`` (ADR 0279), and persisted leftover-map
 *  rank (ADR 0280). The plot names persisted leftover-map complete-case
 *  coverage (ADR 0281), leftover-map item complete-case coverage
 *  (ADR 0282), leftover-map incomplete post coverage (ADR 0283), and
 *  leftover-map incomplete item coverage (ADR 0284). Pair-list post
 *  complete-case coverage fail-closed through leftoverMapCoverageCounts
 *  (ADR 0288), pair-list item complete-case coverage (ADR 0285), pair-list
 *  incomplete post coverage (ADR 0286), pair-list incomplete item
 *  coverage (ADR 0287), grouping comparison complete-case coverage
 *  (ADR 0289), grouping comparison item complete-case coverage
 *  (ADR 0290), grouping comparison incomplete post coverage
 *  (ADR 0291), grouping comparison incomplete item coverage
 *  (ADR 0292), grouping comparison reconstruction
 *  (ADR 0293), grouping comparison explained leftover share
 *  (ADR 0294), grouping comparison unexplained leftover share
 *  (ADR 0295), grouping comparison leftover-map cross share
 *  (ADR 0296), grouping comparison leftover-map unexplained leftover
 *  (ADR 0297), grouping comparison leftover residual
 *  (ADR 0298), grouping comparison leftover observed
 *  (ADR 0299), grouping comparison leftover expected
 *  (ADR 0300), grouping comparison leftover-map rank
 *  (ADR 0301), grouping comparison leftover-map coordinates
 *  (ADR 0302), grouping comparison leftover-map coordinates payload
 *  (ADR 0303), grouping comparison leftover-map graphic display
 *  (ADR 0304), grouping comparison leftover-map axis share on that
 *  graphic (ADR 0305), grouping comparison leftover-map complete-case
 *  coverage on that graphic (ADR 0306), grouping comparison leftover-map
 *  item complete-case coverage on that graphic (ADR 0307), grouping comparison leftover-map
 *  incomplete post coverage on that graphic (ADR 0308), grouping comparison leftover-map
 *  incomplete item coverage on that graphic (ADR 0309), grouping comparison leftover-map
 *  reconstruction on that graphic (ADR 0310), grouping comparison leftover-map
 *  explained leftover share on that graphic (ADR 0311), grouping comparison leftover-map
 *  unexplained leftover share on that graphic (ADR 0312), grouping comparison leftover-map
 *  cross share on that graphic (ADR 0313), and grouping comparison leftover-map
 *  unexplained leftover on that graphic (ADR 0314), and grouping comparison leftover
 *  residual on that graphic (ADR 0315), and grouping comparison leftover
 *  observed on that graphic (ADR 0316), and grouping comparison leftover
 *  expected on that graphic (ADR 0317), and grouping comparison leftover-map
 *  rank on that graphic (ADR 0318), grouping comparison leftover-map
 *  distance on that graphic (ADR 0319), and grouping comparison leftover-map
 *  coordinate ticks on that graphic (ADR 0320), and grouping comparison leftover-map
 *  singular values on that graphic (ADR 0321) caption the pair list or the grouping comparison
 *  strip. ADR 0304 reuses this graphic layout on the grouping comparison
 *  strip. ADR 0305 captions leftover-map axis share on that comparison
 *  graphic from already-named leftover-map axes. ADR 0306 captions leftover-map
 *  complete-case coverage on that comparison graphic from already-named leftover-map
 *  coverage. ADR 0307 captions leftover-map item complete-case coverage on that
 *  comparison graphic from already-named leftover-map coverage. ADR 0308 captions leftover-map
 *  incomplete post coverage on that comparison graphic from already-named leftover-map
 *  coverage. ADR 0309 captions leftover-map incomplete item coverage on that
 *  comparison graphic from already-named leftover-map coverage. ADR 0310 captions leftover-map
 *  reconstruction on that comparison graphic from already-named leftover-map reconstruction.
 *  ADR 0311 captions leftover-map explained leftover share on that comparison graphic from
 *  already-named leftover-map explained leftover share. ADR 0312 captions leftover-map
 *  unexplained leftover share on that comparison graphic from already-named leftover-map
 *  unexplained leftover share. ADR 0313 captions leftover-map
 *  cross share on that comparison graphic from already-named leftover-map
 *  cross share. ADR 0314 captions leftover-map unexplained leftover on that
 *  comparison graphic from already-named leftover-map unexplained leftover.
 *  ADR 0315 captions leftover residual on that comparison graphic from
 *  already-named leftover residual.
 *  ADR 0316 captions leftover observed on that comparison graphic from
 *  already-named leftover observed.
 *  ADR 0317 captions leftover expected on that comparison graphic from
 *  already-named leftover expected.
 *  ADR 0318 captions leftover-map rank on that comparison graphic from
 *  already-named leftover-map rank.
 *  ADR 0319 captions leftover-map distance on that comparison graphic from
 *  already-named leftover-map distance.
 *  ADR 0320 captions leftover-map coordinate ticks on that comparison graphic from
 *  already-named leftover-map coordinates.
 *  ADR 0321 captions leftover-map singular values on that comparison graphic from
 *  already-named leftover-map axes.
 *  ADR 0322 captions leftover-axis report badges with persisted leftover-map
 *  singular values, not this graphic.
 *  ADR 0323 captions leftover-axis report badges on the grouping comparison strip
 *  with persisted leftover-map singular values, not this graphic.
 *  ADR 0324 captions leftover-map graphic-display axes with persisted leftover-map
 *  singular values `σ_k`.
 *  ADR 0326 fail-closes leftover-map comparison graphic leftover-map axis leftover-map
 *  singular values through leftoverMapComparePlotAxisBadge.
 *  ADR 0327 fail-closes leftover-map graphic leftover-map axis ticks leftover-map
 *  singular values through leftoverMapPlotTickAxisBadge independently of leftover-map
 *  axis share.
 *  ADR 0328 fail-closes leftover-map comparison graphic leftover-map axis ticks leftover-map
 *  singular values through leftoverMapComparePlotTickAxisBadge independently of leftover-map
 *  axis share.
 *  ADR 0329 fail-closes leftover-map comparison leftover-axis ticks leftover-map
 *  singular values through leftoverMapCompareAxisTickBadge independently of leftover-map
 *  axis share, not this graphic.
 *  ADR 0330 fail-closes leftover-map leftover-axis ticks leftover-map
 *  singular values through leftoverMapAxisTickBadge independently of leftover-map
 *  axis share, not this graphic.
 *  ADR 0331 fail-closes leftover-map comparison graphic leftover-map axis ticks leftover-map
 *  axis share through leftoverMapComparePlotTickAxisBadge independently of leftover-map
 *  singular values.
 *  ADR 0332 fail-closes leftover-map graphic leftover-map axis ticks leftover-map
 *  axis share through leftoverMapPlotTickAxisBadge independently of leftover-map
 *  singular values.
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

export const LEFTOVER_MAP_COMPARE_PLOT_TICK =
  "leftover map comparison graphic leftover-map axis {axis} tick {value}";

export const LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE =
  "leftover-map distance {label}";

export const LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_DISTANCE =
  "leftover map comparison graphic leftover-map distance {label}";

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

export { LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED } from "./leftoverObservedExpected";

export const LEFTOVER_MAP_PLOT_SEGMENT_RANK =
  "leftover-map rank {label}";

export { LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK } from "./leftoverMapRank";

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
    const crossShareLabel = formatLeftoverMapCrossShare(pair.leftover_map_cross_share);
    const unexplainedLeftoverLabel = formatLeftoverMapUnexplained(
      pair.leftover_map_unexplained,
    );
    const residualLabel = formatLeftoverMapResidual(pair.leftover_residual);
    const observedLabel = formatLeftoverMapObserved(pair.observed_response);
    const expectedLabel = formatLeftoverMapExpected(pair.expected_response);
    const rankLabel = formatLeftoverMapRank(pair.leftover_map_rank);
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
    const crossShareY = leftoverMapStackedCaptionY(
      labelPosition.labelY,
      (distanceLabel !== null ? 1 : 0) +
        (reconstructionLabel !== null ? 1 : 0) +
        (explainedShareLabel !== null ? 1 : 0) +
        (unexplainedShareLabel !== null ? 1 : 0),
    );
    const unexplainedLeftoverY = leftoverMapStackedCaptionY(
      labelPosition.labelY,
      (distanceLabel !== null ? 1 : 0) +
        (reconstructionLabel !== null ? 1 : 0) +
        (explainedShareLabel !== null ? 1 : 0) +
        (unexplainedShareLabel !== null ? 1 : 0) +
        (crossShareLabel !== null ? 1 : 0),
    );
    const residualY = leftoverMapStackedCaptionY(
      labelPosition.labelY,
      (distanceLabel !== null ? 1 : 0) +
        (reconstructionLabel !== null ? 1 : 0) +
        (explainedShareLabel !== null ? 1 : 0) +
        (unexplainedShareLabel !== null ? 1 : 0) +
        (crossShareLabel !== null ? 1 : 0) +
        (unexplainedLeftoverLabel !== null ? 1 : 0),
    );
    const observedY = leftoverMapStackedCaptionY(
      labelPosition.labelY,
      (distanceLabel !== null ? 1 : 0) +
        (reconstructionLabel !== null ? 1 : 0) +
        (explainedShareLabel !== null ? 1 : 0) +
        (unexplainedShareLabel !== null ? 1 : 0) +
        (crossShareLabel !== null ? 1 : 0) +
        (unexplainedLeftoverLabel !== null ? 1 : 0) +
        (residualLabel !== null ? 1 : 0),
    );
    const expectedY = leftoverMapStackedCaptionY(
      labelPosition.labelY,
      (distanceLabel !== null ? 1 : 0) +
        (reconstructionLabel !== null ? 1 : 0) +
        (explainedShareLabel !== null ? 1 : 0) +
        (unexplainedShareLabel !== null ? 1 : 0) +
        (crossShareLabel !== null ? 1 : 0) +
        (unexplainedLeftoverLabel !== null ? 1 : 0) +
        (residualLabel !== null ? 1 : 0) +
        (observedLabel !== null ? 1 : 0),
    );
    const rankY = leftoverMapStackedCaptionY(
      labelPosition.labelY,
      (distanceLabel !== null ? 1 : 0) +
        (reconstructionLabel !== null ? 1 : 0) +
        (explainedShareLabel !== null ? 1 : 0) +
        (unexplainedShareLabel !== null ? 1 : 0) +
        (crossShareLabel !== null ? 1 : 0) +
        (unexplainedLeftoverLabel !== null ? 1 : 0) +
        (residualLabel !== null ? 1 : 0) +
        (observedLabel !== null ? 1 : 0) +
        (expectedLabel !== null ? 1 : 0),
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
      reconstructionX: labelPosition.labelX,
      reconstructionY,
      explainedShareX: labelPosition.labelX,
      explainedShareY,
      unexplainedShareX: labelPosition.labelX,
      unexplainedShareY,
      crossShareX: labelPosition.labelX,
      crossShareY,
      unexplainedLeftoverX: labelPosition.labelX,
      unexplainedLeftoverY,
      residualX: labelPosition.labelX,
      residualY,
      observedX: labelPosition.labelX,
      observedY,
      expectedX: labelPosition.labelX,
      expectedY,
      rankX: labelPosition.labelX,
      rankY,
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
