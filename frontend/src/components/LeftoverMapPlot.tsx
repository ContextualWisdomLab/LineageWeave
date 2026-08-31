import type { LeftoverMapAxis, LeftoverMapCoverage, LeftoverPair } from "../api";
import { t, tf } from "../i18n";
import {
  leftoverMapCoverageCounts,
  leftoverMapIncompleteItemCount,
  leftoverMapIncompletePostCount,
  leftoverMapItemCoverageCounts,
  LEFTOVER_MAP_COMPARE_PLOT_COVERAGE_LABEL,
  LEFTOVER_MAP_COMPARE_PLOT_ITEM_COVERAGE_LABEL,
  LEFTOVER_MAP_COMPARE_PLOT_INCOMPLETE_POST_LABEL,
  LEFTOVER_MAP_COMPARE_PLOT_INCOMPLETE_ITEM_LABEL,
  LEFTOVER_MAP_PLOT_COVERAGE,
  LEFTOVER_MAP_PLOT_COVERAGE_LABEL,
  LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM,
  LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM_LABEL,
  LEFTOVER_MAP_PLOT_INCOMPLETE_POST,
  LEFTOVER_MAP_PLOT_INCOMPLETE_POST_LABEL,
  LEFTOVER_MAP_PLOT_ITEM_COVERAGE,
  LEFTOVER_MAP_PLOT_ITEM_COVERAGE_LABEL,
} from "../leftoverMapCoverage";
import {
  leftoverShareForAxis,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_1,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_2,
} from "../leftoverMapPlotAxisShare";
import {
  leftoverMapComparePlotAxisBadge,
  leftoverMapComparePlotTickAxisBadge,
  leftoverMapPlotAxisBadge,
  leftoverMapPlotTickAxisBadge,
  leftoverSingularForAxis,
} from "../leftoverMapPlotAxisSingular";
import {
  firstPlottablePairForPost,
  layoutLeftoverMapPlot,
  leftoverMapPlotCriterionBadge,
  leftoverMapComparePlotCriterionBadge,
  leftoverMapComparePlotPostBadge,
  leftoverMapPlotPostBadge,
  LEFTOVER_MAP_COMPARE_PLOT_CAPTION,
  LEFTOVER_MAP_COMPARE_PLOT_LABEL,
  LEFTOVER_MAP_COMPARE_PLOT_SVG,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RECONSTRUCTION,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPLAINED_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_CROSS_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_OBSERVED,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_DISTANCE,
  LEFTOVER_MAP_PLOT_CAPTION,
  LEFTOVER_MAP_PLOT_POST_ACTION_OMITTED,
  LEFTOVER_MAP_PLOT_SEGMENT_CROSS_SHARE,
  LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE,
  LEFTOVER_MAP_PLOT_SEGMENT_EXPLAINED_SHARE,
  LEFTOVER_MAP_PLOT_SEGMENT_EXPECTED,
  LEFTOVER_MAP_PLOT_SEGMENT_OBSERVED,
  LEFTOVER_MAP_PLOT_SEGMENT_RANK,
  LEFTOVER_MAP_PLOT_SEGMENT_RECONSTRUCTION,
  LEFTOVER_MAP_PLOT_SEGMENT_RESIDUAL,
  LEFTOVER_MAP_PLOT_SEGMENT_UNEXPLAINED,
  LEFTOVER_MAP_PLOT_SEGMENT_UNEXPLAINED_SHARE,
} from "../leftoverMapPlotLayout";
import "./LeftoverMapPlot.css";

export type LeftoverMapPlotVariant = "report" | "comparison";

export type LeftoverMapPlotProps = {
  pairs: LeftoverPair[];
  leftoverMapAxes?: LeftoverMapAxis[];
  leftoverMapCoverage?: LeftoverMapCoverage | null;
  criterionLabel: (criterionCode: string) => string;
  onSelectPost: (pair: LeftoverPair) => void;
  variant?: LeftoverMapPlotVariant;
};

function diamondPoints(x: number, y: number, radius: number): string {
  return `${x},${y - radius} ${x + radius},${y} ${x},${y + radius} ${x - radius},${y}`;
}

function leftoverMapPlotAxisText(
  axisIndex: 1 | 2,
  leftoverMapAxes: LeftoverMapAxis[] | undefined,
  variant: LeftoverMapPlotVariant,
): string {
  const leftoverShare = leftoverShareForAxis(leftoverMapAxes, axisIndex);
  const leftoverSingular = leftoverSingularForAxis(leftoverMapAxes, axisIndex);
  if (variant === "comparison") {
    const badge = leftoverMapComparePlotAxisBadge(axisIndex, leftoverSingular, leftoverShare);
    if (badge === null) {
      return t(axisIndex === 1 ? LEFTOVER_MAP_COMPARE_PLOT_AXIS_1 : LEFTOVER_MAP_COMPARE_PLOT_AXIS_2);
    }
    return tf(badge.key, badge.values);
  }
  const badge = leftoverMapPlotAxisBadge(axisIndex, leftoverSingular, leftoverShare);
  if (badge === null) {
    return t(axisIndex === 1 ? "leftover-map axis 1" : "leftover-map axis 2");
  }
  return tf(badge.key, badge.values);
}

function leftoverMapPlotTickText(
  axisIndex: number,
  tickLabel: string,
  leftoverMapAxes: LeftoverMapAxis[] | undefined,
  variant: LeftoverMapPlotVariant,
): string {
  const leftoverSingular = leftoverSingularForAxis(leftoverMapAxes, axisIndex);
  const leftoverShare = leftoverShareForAxis(leftoverMapAxes, axisIndex);
  if (variant === "comparison") {
    const badge = leftoverMapComparePlotTickAxisBadge(
      axisIndex,
      tickLabel,
      leftoverSingular,
      leftoverShare,
    );
    return tf(badge.key, badge.values);
  }
  const badge = leftoverMapPlotTickAxisBadge(axisIndex, tickLabel, leftoverSingular, leftoverShare);
  return tf(badge.key, badge.values);
}

function leftoverMapPlotCriterionText(
  marker: { label: string; axis1: number; axis2: number },
  variant: LeftoverMapPlotVariant,
): string {
  if (variant === "comparison") {
    const badge = leftoverMapComparePlotCriterionBadge(marker.label, marker.axis1, marker.axis2);
    if (badge === null) {
      return `${t("Criterion ζ")} ${marker.label}`;
    }
    return tf(badge.key, badge.values);
  }
  const badge = leftoverMapPlotCriterionBadge(marker.label, marker.axis1, marker.axis2);
  if (badge === null) {
    return `${t("Criterion ζ")} ${marker.label}`;
  }
  return tf(badge.key, badge.values);
}

function leftoverMapPlotPostText(
  marker: { label: string; axis1: number; axis2: number },
  variant: LeftoverMapPlotVariant,
): string {
  if (variant === "comparison") {
    const badge = leftoverMapComparePlotPostBadge(marker.label, marker.axis1, marker.axis2);
    if (badge === null) {
      return tf(LEFTOVER_MAP_PLOT_POST_ACTION_OMITTED, { title: marker.label });
    }
    return tf(badge.key, badge.values);
  }
  const badge = leftoverMapPlotPostBadge(marker.label, marker.axis1, marker.axis2);
  if (badge === null) {
    return tf(LEFTOVER_MAP_PLOT_POST_ACTION_OMITTED, { title: marker.label });
  }
  return tf(badge.key, badge.values);
}

/**
 * Gabriel leftover-map graphic display of persisted ``ξ_{1:2}`` / ``ζ_{1:2}``.
 *
 * Person markers are posts; item markers are leftover criteria. Click a
 * post marker to open that post. Caption leftover-map graphic leftover-map
 * criterion markers with persisted leftover-map item coordinates ``ζ_{1:2}``
 * when leftoverMapPlotCriterionBadge returns a usable leftover-map criterion
 * leftover-map item coordinate caption. Caption leftover-map origin on leftover-map graphic leftover-map
 * criterion leftover-map item coordinates independently of leftover-map person coordinates when leftoverMapPlotCoordinatePairIsOrigin
 * returns true. Caption leftover-map comparison graphic leftover-map
 * criterion markers with persisted leftover-map item coordinates ``ζ_{1:2}``
 * when leftoverMapComparePlotCriterionBadge returns a usable leftover-map comparison
 * graphic leftover-map criterion leftover-map item coordinate caption. Caption leftover-map
 * comparison graphic leftover-map post markers with persisted leftover-map person coordinates
 * ``ξ_{1:2}`` when leftoverMapComparePlotPostBadge returns a usable leftover-map comparison
 * graphic leftover-map post leftover-map person coordinate caption. Caption leftover-map graphic leftover-map
 * post markers with persisted leftover-map person coordinates
 * ``ξ_{1:2}`` when leftoverMapPlotPostBadge returns a usable leftover-map graphic leftover-map
 * post leftover-map person coordinate caption. Caption leftover-map axes with persisted
 * leftover-map singular values ``σ_k`` and Gabriel inertia share when finite,
 * including rank-0 zero-share axes.
 * Axis ticks name persisted leftover-map coordinates so ξ / ζ on the
 * pair row match the plot. Pair segments name persisted leftover-map
 * distance ``d``, leftover-map reconstruction ``R̂``, leftover-map
 * explained leftover share ``e``, leftover-map unexplained leftover
 * share ``s``, leftover-map cross share ``x``, leftover-map
 * unexplained leftover ``U``, leftover residual ``R``, leftover
 * observed ``Y``, leftover expected ``E``, and leftover-map rank so the
 * pair-row badges match the graphic. Name leftover-map complete-case
 * coverage, leftover-map item complete-case coverage, leftover-map
 * incomplete post coverage, and leftover-map incomplete item coverage
 * on the figure when those persisted post and criterion counts are usable.
 * Omit that distance caption when ``d`` is missing or non-finite. Omit
 * that reconstruction caption when ``R̂`` is missing or non-finite. Omit
 * that explained leftover share caption when ``e`` is missing or
 * non-finite. Omit that unexplained leftover share caption when ``s`` is
 * missing or non-finite. Omit that leftover-map cross share caption when
 * ``x`` is missing or non-finite. Omit that unexplained leftover caption
 * when ``U`` is missing or non-finite. Omit that leftover residual
 * caption when ``R`` is missing or non-finite. Omit that leftover observed
 * caption when ``Y`` is missing or non-finite. Omit that leftover expected
 * caption when ``E`` is missing or non-finite. Omit that leftover-map rank
 * caption when rank is missing, negative, or not an integer. Omit that leftover-map
 * coverage caption when coverage is missing or not usable complete-case integers.
 * Omit that leftover-map item coverage caption when item coverage is missing or
 * not usable complete-case integers. Omit that leftover-map incomplete post
 * caption when incomplete post coverage is missing or not a usable integer.
 * Omit that leftover-map incomplete item caption when incomplete item
 * coverage is missing or not a usable integer.
 * Omit that axis singular-value badge when ``σ_k`` is missing, non-finite,
 * or negative, independently of leftover-map axis share. Omit that axis badge when share is
 * missing or non-finite and keep the existing leftover-map axis text,
 * including any leftover-map comparison graphic leftover-map axis singular value.
 * Omit the plot when no pair has four finite leftover-map coordinates.
 * ADR 0304 reuses this graphic on the grouping comparison strip from
 * already-named leftover-map coordinates. ADR 0305 captions leftover-map axis
 * share on that comparison graphic from already-named leftover-map axes
 * with distinct leftover map comparison axis labels. ADR 0306 captions leftover-map
 * complete-case coverage on that comparison graphic from already-named
 * leftover-map coverage with distinct leftover map comparison graphic coverage
 * labels and does not caption leftover-map incomplete coverage on that
 * comparison plot. ADR 0307 captions leftover-map item complete-case
 * coverage on that comparison graphic from already-named leftover-map
 * coverage with distinct leftover map comparison graphic item coverage
 * labels and does not caption leftover-map incomplete item coverage on that
 * comparison plot. ADR 0308 captions leftover-map incomplete post coverage
 * on that comparison graphic from already-named leftover-map coverage with
 * distinct leftover map comparison graphic incomplete posts labels. ADR 0309
 * captions leftover-map incomplete item coverage on that comparison graphic
 * from already-named leftover-map coverage with distinct leftover map
 * comparison graphic incomplete items labels. ADR 0310 captions leftover-map
 * reconstruction on that comparison graphic from already-named leftover-map
 * reconstruction with distinct leftover map comparison graphic reconstruction
 * labels. ADR 0311 captions leftover-map explained leftover share on that
 * comparison graphic from already-named leftover-map explained leftover share
 * with distinct leftover map comparison graphic explained leftover share
 * labels. ADR 0312 captions leftover-map unexplained leftover share on that
 * comparison graphic from already-named leftover-map unexplained leftover share
 * with distinct leftover map comparison graphic unexplained leftover share
 * labels. ADR 0313 captions leftover-map cross share on that
 * comparison graphic from already-named leftover-map cross share
 * with distinct leftover map comparison graphic cross share
 * labels. ADR 0314 captions leftover-map unexplained leftover on that
 * comparison graphic from already-named leftover-map unexplained leftover
 * with distinct leftover map comparison graphic unexplained leftover
 * labels. ADR 0315 captions leftover residual on that
 * comparison graphic from already-named leftover residual
 * with distinct leftover map comparison graphic leftover residual
 * labels. ADR 0316 captions leftover observed on that
 * comparison graphic from already-named leftover observed
 * with distinct leftover map comparison graphic leftover observed
 * labels. ADR 0317 captions leftover expected on that
 * comparison graphic from already-named leftover expected
 * with distinct leftover map comparison graphic leftover expected
 * labels. ADR 0318 captions leftover-map rank on that
 * comparison graphic from already-named leftover-map rank
 * with distinct leftover map comparison graphic leftover-map rank
 * labels. ADR 0319 captions leftover-map distance on that
 * comparison graphic from already-named leftover-map distance
 * with distinct leftover map comparison graphic leftover-map distance
 * labels. ADR 0320 captions leftover-map coordinate ticks on that
 * comparison graphic from already-named leftover-map coordinates
 * with distinct leftover map comparison graphic leftover-map axis tick
 * labels. ADR 0321 captions leftover-map singular values on that
 * comparison graphic from already-named leftover-map axes
 * with distinct leftover map comparison graphic leftover-map axis σ
 * labels. ADR 0322 captions leftover-axis report badges with persisted
 * leftover-map singular values, not this graphic. ADR 0323 captions leftover-axis
 * report badges on the grouping comparison strip with persisted leftover-map
 * singular values, not this graphic. ADR 0324 captions leftover-map
 * graphic-display axes with persisted leftover-map singular values.
 * ADR 0326 fail-closes leftover-map comparison graphic leftover-map axis leftover-map
 * singular values through leftoverMapComparePlotAxisBadge.
 * ADR 0327 fail-closes leftover-map graphic leftover-map axis ticks leftover-map
 * singular values through leftoverMapPlotTickAxisBadge independently of leftover-map
 * axis share.
 * ADR 0328 fail-closes leftover-map comparison graphic leftover-map axis ticks leftover-map
 * singular values through leftoverMapComparePlotTickAxisBadge independently of leftover-map
 * axis share.
 * ADR 0331 fail-closes leftover-map comparison graphic leftover-map axis ticks leftover-map
 * axis share through leftoverMapComparePlotTickAxisBadge independently of leftover-map
 * singular values.
 * ADR 0332 fail-closes leftover-map graphic leftover-map axis ticks leftover-map
 * axis share through leftoverMapPlotTickAxisBadge independently of leftover-map
 * singular values.
 * ADR 0343 fail-closes leftover-map graphic leftover-map axis origin ticks through
 * leftoverMapPlotTickAxisBadge independently of leftover-map axis share and leftover-map
 * singular values.
 * ADR 0344 fail-closes leftover-map comparison graphic leftover-map axis origin ticks through
 * leftoverMapComparePlotTickAxisBadge independently of leftover-map axis share and leftover-map
 * singular values.
 * ADR 0345 fail-closes leftover-map comparison leftover-axis origin ticks through
 * leftoverMapCompareAxisTickBadge independently of leftover-map axis share and leftover-map
 * singular values.
 * ADR 0346 fail-closes leftover-map leftover-axis origin ticks through
 * leftoverMapAxisTickBadge independently of leftover-map axis share and leftover-map
 * singular values.
 * ADR 0347 fail-closes leftover-map graphic leftover-map criterion leftover-map origin leftover-map
 * item coordinates through leftoverMapPlotCriterionBadge independently of leftover-map
 * person coordinates.
 * Never invent a leftover score.
 */
export function LeftoverMapPlot({
  pairs,
  leftoverMapAxes,
  leftoverMapCoverage,
  criterionLabel,
  onSelectPost,
  variant = "report",
}: LeftoverMapPlotProps) {
  const layout = layoutLeftoverMapPlot(pairs, criterionLabel);
  if (layout === null) {
    return null;
  }
  const coverageCounts = leftoverMapCoverageCounts(leftoverMapCoverage);
  const itemCoverageCounts = leftoverMapItemCoverageCounts(leftoverMapCoverage);
  const incompletePostCount = leftoverMapIncompletePostCount(leftoverMapCoverage);
  const incompleteItemCount = leftoverMapIncompleteItemCount(leftoverMapCoverage);

  const openPost = (postId: string) => {
    const pair = firstPlottablePairForPost(pairs, postId);
    if (pair) {
      onSelectPost(pair as LeftoverPair);
    }
  };

  return (
    <figure
      className="leftover-map-plot"
      aria-label={t(variant === "comparison" ? LEFTOVER_MAP_COMPARE_PLOT_LABEL : "Leftover-map graphic display")}
    >
      <figcaption className="leftover-map-plot-caption">
        {t(variant === "comparison" ? LEFTOVER_MAP_COMPARE_PLOT_CAPTION : LEFTOVER_MAP_PLOT_CAPTION)}
      </figcaption>
      {coverageCounts !== null ? (
        <p
          className="leftover-map-plot-coverage"
          role="note"
          aria-label={t(
            variant === "comparison"
              ? LEFTOVER_MAP_COMPARE_PLOT_COVERAGE_LABEL
              : LEFTOVER_MAP_PLOT_COVERAGE_LABEL,
          )}
        >
          {tf(LEFTOVER_MAP_PLOT_COVERAGE, coverageCounts)}
        </p>
      ) : null}
      {itemCoverageCounts !== null ? (
        <p
          className="leftover-map-plot-item-coverage"
          role="note"
          aria-label={t(
            variant === "comparison"
              ? LEFTOVER_MAP_COMPARE_PLOT_ITEM_COVERAGE_LABEL
              : LEFTOVER_MAP_PLOT_ITEM_COVERAGE_LABEL,
          )}
        >
          {tf(LEFTOVER_MAP_PLOT_ITEM_COVERAGE, itemCoverageCounts)}
        </p>
      ) : null}
      {incompletePostCount !== null ? (
        <p
          className="leftover-map-plot-incomplete-posts"
          role="note"
          aria-label={t(
            variant === "comparison"
              ? LEFTOVER_MAP_COMPARE_PLOT_INCOMPLETE_POST_LABEL
              : LEFTOVER_MAP_PLOT_INCOMPLETE_POST_LABEL,
          )}
        >
          {tf(LEFTOVER_MAP_PLOT_INCOMPLETE_POST, incompletePostCount)}
        </p>
      ) : null}
      {incompleteItemCount !== null ? (
        <p
          className="leftover-map-plot-incomplete-items"
          role="note"
          aria-label={t(
            variant === "comparison"
              ? LEFTOVER_MAP_COMPARE_PLOT_INCOMPLETE_ITEM_LABEL
              : LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM_LABEL,
          )}
        >
          {tf(LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM, incompleteItemCount)}
        </p>
      ) : null}
      <ul className="leftover-map-plot-legend">
        <li>
          <span className="leftover-map-plot-legend-swatch person" aria-hidden="true" />
          {t("Post ξ")}
        </li>
        <li>
          <span className="leftover-map-plot-legend-swatch item" aria-hidden="true" />
          {t("Criterion ζ")}
        </li>
      </ul>
      <div className="leftover-map-plot-viewport" tabIndex={0}>
        <svg
          className="leftover-map-plot-svg"
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          role="group"
          aria-label={t(variant === "comparison" ? LEFTOVER_MAP_COMPARE_PLOT_SVG : "Leftover map")}
        >
          <line
            className="leftover-map-plot-axis"
            x1={layout.originX}
            y1={0}
            x2={layout.originX}
            y2={layout.height}
          />
          <line
            className="leftover-map-plot-axis"
            x1={0}
            y1={layout.originY}
            x2={layout.width}
            y2={layout.originY}
          />
          <text className="leftover-map-plot-axis-label" x={layout.width - 8} y={layout.originY - 8} textAnchor="end">
            {leftoverMapPlotAxisText(1, leftoverMapAxes, variant)}
          </text>
          <text className="leftover-map-plot-axis-label" x={layout.originX + 8} y={16}>
            {leftoverMapPlotAxisText(2, leftoverMapAxes, variant)}
          </text>
          {layout.ticks.map((tick) => (
            <g
              key={`tick:${tick.axis}:${tick.label}`}
              className="leftover-map-plot-tick"
              aria-label={leftoverMapPlotTickText(
                tick.axis,
                tick.label,
                leftoverMapAxes,
                variant,
              )}
            >
              <line x1={tick.x} y1={tick.y} x2={tick.tickX2} y2={tick.tickY2} />
              <text
                className="leftover-map-plot-tick-label"
                x={tick.axis === 1 ? tick.x : tick.tickX2 - 2}
                y={tick.axis === 1 ? tick.tickY2 + 12 : tick.y + 4}
                textAnchor={tick.axis === 1 ? "middle" : "end"}
              >
                {tick.label}
              </text>
            </g>
          ))}
          {layout.segments.map((segment) => (
            <g key={`${segment.pairKind}:${segment.postId}:${segment.criterionCode}`}>
              <line
                className={`leftover-map-plot-segment ${segment.pairKind}`}
                x1={segment.x1}
                y1={segment.y1}
                x2={segment.x2}
                y2={segment.y2}
              />
              {segment.distanceLabel !== null ? (
                <text
                  className="leftover-map-plot-segment-label"
                  x={segment.labelX}
                  y={segment.labelY}
                  textAnchor="middle"
                  aria-label={tf(
                    variant === "comparison"
                      ? LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_DISTANCE
                      : LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE,
                    { label: segment.distanceLabel },
                  )}
                >
                  {segment.distanceLabel}
                </text>
              ) : null}
              {segment.reconstructionLabel !== null ? (
                <text
                  className="leftover-map-plot-segment-label leftover-map-plot-segment-reconstruction"
                  x={segment.reconstructionX}
                  y={segment.reconstructionY}
                  textAnchor="middle"
                  aria-label={tf(
                    variant === "comparison"
                      ? LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RECONSTRUCTION
                      : LEFTOVER_MAP_PLOT_SEGMENT_RECONSTRUCTION,
                    { label: segment.reconstructionLabel },
                  )}
                >
                  {segment.reconstructionLabel}
                </text>
              ) : null}
              {segment.explainedShareLabel !== null ? (
                <text
                  className="leftover-map-plot-segment-label leftover-map-plot-segment-explained-share"
                  x={segment.explainedShareX}
                  y={segment.explainedShareY}
                  textAnchor="middle"
                  aria-label={tf(
                    variant === "comparison"
                      ? LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPLAINED_SHARE
                      : LEFTOVER_MAP_PLOT_SEGMENT_EXPLAINED_SHARE,
                    { label: segment.explainedShareLabel },
                  )}
                >
                  {segment.explainedShareLabel}
                </text>
              ) : null}
              {segment.unexplainedShareLabel !== null ? (
                <text
                  className="leftover-map-plot-segment-label leftover-map-plot-segment-unexplained-share"
                  x={segment.unexplainedShareX}
                  y={segment.unexplainedShareY}
                  textAnchor="middle"
                  aria-label={tf(
                    variant === "comparison"
                      ? LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED_SHARE
                      : LEFTOVER_MAP_PLOT_SEGMENT_UNEXPLAINED_SHARE,
                    { label: segment.unexplainedShareLabel },
                  )}
                >
                  {segment.unexplainedShareLabel}
                </text>
              ) : null}
              {segment.crossShareLabel !== null ? (
                <text
                  className="leftover-map-plot-segment-label leftover-map-plot-segment-cross-share"
                  x={segment.crossShareX}
                  y={segment.crossShareY}
                  textAnchor="middle"
                  aria-label={tf(
                    variant === "comparison"
                      ? LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_CROSS_SHARE
                      : LEFTOVER_MAP_PLOT_SEGMENT_CROSS_SHARE,
                    { label: segment.crossShareLabel },
                  )}
                >
                  {segment.crossShareLabel}
                </text>
              ) : null}
              {segment.unexplainedLeftoverLabel !== null ? (
                <text
                  className="leftover-map-plot-segment-label leftover-map-plot-segment-unexplained"
                  x={segment.unexplainedLeftoverX}
                  y={segment.unexplainedLeftoverY}
                  textAnchor="middle"
                  aria-label={tf(
                    variant === "comparison"
                      ? LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED
                      : LEFTOVER_MAP_PLOT_SEGMENT_UNEXPLAINED,
                    { label: segment.unexplainedLeftoverLabel },
                  )}
                >
                  {segment.unexplainedLeftoverLabel}
                </text>
              ) : null}
              {segment.residualLabel !== null ? (
                <text
                  className="leftover-map-plot-segment-label leftover-map-plot-segment-residual"
                  x={segment.residualX}
                  y={segment.residualY}
                  textAnchor="middle"
                  aria-label={tf(
                    variant === "comparison"
                      ? LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL
                      : LEFTOVER_MAP_PLOT_SEGMENT_RESIDUAL,
                    { label: segment.residualLabel },
                  )}
                >
                  {segment.residualLabel}
                </text>
              ) : null}
              {segment.observedLabel !== null ? (
                <text
                  className="leftover-map-plot-segment-label leftover-map-plot-segment-observed"
                  x={segment.observedX}
                  y={segment.observedY}
                  textAnchor="middle"
                  aria-label={tf(
                    variant === "comparison"
                      ? LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_OBSERVED
                      : LEFTOVER_MAP_PLOT_SEGMENT_OBSERVED,
                    { label: segment.observedLabel },
                  )}
                >
                  {segment.observedLabel}
                </text>
              ) : null}
              {segment.expectedLabel !== null ? (
                <text
                  className="leftover-map-plot-segment-label leftover-map-plot-segment-expected"
                  x={segment.expectedX}
                  y={segment.expectedY}
                  textAnchor="middle"
                  aria-label={tf(
                    variant === "comparison"
                      ? LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED
                      : LEFTOVER_MAP_PLOT_SEGMENT_EXPECTED,
                    { label: segment.expectedLabel },
                  )}
                >
                  {segment.expectedLabel}
                </text>
              ) : null}
              {segment.rankLabel !== null ? (
                <text
                  className="leftover-map-plot-segment-label leftover-map-plot-segment-rank"
                  x={segment.rankX}
                  y={segment.rankY}
                  textAnchor="middle"
                  aria-label={tf(
                    variant === "comparison"
                      ? LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK
                      : LEFTOVER_MAP_PLOT_SEGMENT_RANK,
                    { label: segment.rankLabel },
                  )}
                >
                  {segment.rankLabel}
                </text>
              ) : null}
            </g>
          ))}
          {layout.items.map((marker) => (
            <g key={`item:${marker.id}`} aria-label={leftoverMapPlotCriterionText(marker, variant)}>
              <polygon className="leftover-map-plot-item" points={diamondPoints(marker.x, marker.y, 7)} />
              <text className="leftover-map-plot-label" x={marker.x + 10} y={marker.y + 14}>
                {marker.label}
              </text>
            </g>
          ))}
          {layout.persons.map((marker) => {
            return (
              <g
                key={`person:${marker.id}`}
                className="leftover-map-plot-marker"
                role="button"
                tabIndex={0}
                aria-label={leftoverMapPlotPostText(marker, variant)}
                onClick={() => openPost(marker.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openPost(marker.id);
                  }
                }}
              >
                <circle className="leftover-map-plot-person-hit" cx={marker.x} cy={marker.y} r={22} />
                <circle className="leftover-map-plot-person" cx={marker.x} cy={marker.y} r={6} />
                <text className="leftover-map-plot-label" x={marker.x + 10} y={marker.y - 10}>
                  {marker.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </figure>
  );
}
