import type { LeftoverMapAxis, LeftoverMapCoverage, LeftoverPair } from "../api";
import { t, tf } from "../i18n";
import { formatLeftoverMapCoordinatePair } from "../leftoverMapCoordinates";
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
  formatLeftoverMapPlotAxisShare,
  leftoverShareForAxis,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_1,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_2,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
  LEFTOVER_MAP_PLOT_AXIS_SHARE,
} from "../leftoverMapPlotAxisShare";
import {
  formatLeftoverMapPlotAxisSingular,
  leftoverSingularForAxis,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
} from "../leftoverMapPlotAxisSingular";
import {
  firstPlottablePairForPost,
  layoutLeftoverMapPlot,
  leftoverMapComparePlotCriterionBadge,
  leftoverMapComparePlotPostBadge,
  leftoverMapPlotCriterionBadge,
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
  LEFTOVER_MAP_PLOT_CAPTION,
  LEFTOVER_MAP_PLOT_POST_ACTION,
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
  LEFTOVER_MAP_PLOT_TICK,
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
  const percent = formatLeftoverMapPlotAxisShare(
    leftoverShareForAxis(leftoverMapAxes, axisIndex),
  );
  const singular = formatLeftoverMapPlotAxisSingular(
    leftoverSingularForAxis(leftoverMapAxes, axisIndex),
  );
  if (variant === "comparison") {
    if (singular === null) {
      if (percent === null) {
        return t(axisIndex === 1 ? LEFTOVER_MAP_COMPARE_PLOT_AXIS_1 : LEFTOVER_MAP_COMPARE_PLOT_AXIS_2);
      }
      return tf(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE, { axis: axisIndex, share: percent });
    }
    if (percent === null) {
      return tf(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR, { axis: axisIndex, value: singular });
    }
    return tf(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE, {
      axis: axisIndex,
      value: singular,
      share: percent,
    });
  }
  if (percent === null) {
    return t(axisIndex === 1 ? "leftover-map axis 1" : "leftover-map axis 2");
  }
  return tf(LEFTOVER_MAP_PLOT_AXIS_SHARE, { axis: axisIndex, share: percent });
}

function leftoverMapPlotCriterionText(
  marker: { label: string; axis1: number; axis2: number },
  variant: LeftoverMapPlotVariant,
): string {
  if (variant === "comparison") {
    const badge = leftoverMapComparePlotCriterionBadge(marker.label, marker.axis1, marker.axis2);
    if (badge === null) {
      return `${t(LEFTOVER_MAP_COMPARE_PLOT_LABEL)}: ${t("Criterion ζ")} ${marker.label}`;
    }
    return `${t(LEFTOVER_MAP_COMPARE_PLOT_LABEL)}: ${t("Criterion ζ")} ${badge.values.label} · ζ ${badge.values.item}`;
  }
  const badge = leftoverMapPlotCriterionBadge(marker.label, marker.axis1, marker.axis2);
  if (badge === null) {
    return `${t("Criterion ζ")} ${marker.label}`;
  }
  return `${t("Criterion ζ")} ${badge.values.label} · ζ ${badge.values.item}`;
}

function leftoverMapPlotPostText(
  marker: { label: string; axis1: number; axis2: number },
  variant: LeftoverMapPlotVariant,
): string {
  if (variant === "comparison") {
    const badge = leftoverMapComparePlotPostBadge(marker.label, marker.axis1, marker.axis2);
    if (badge === null) {
      return `${t(LEFTOVER_MAP_COMPARE_PLOT_LABEL)}: ${t("Post ξ")} ${marker.label}`;
    }
    return `${t(LEFTOVER_MAP_COMPARE_PLOT_LABEL)}: ${tf(LEFTOVER_MAP_PLOT_POST_ACTION, badge.values)}`;
  }
  const person = formatLeftoverMapCoordinatePair(marker.axis1, marker.axis2) ?? "";
  return tf(LEFTOVER_MAP_PLOT_POST_ACTION, {
    title: marker.label,
    person,
  });
}

/**
 * Gabriel leftover-map graphic display of persisted ``ξ_{1:2}`` / ``ζ_{1:2}``.
 *
 * Report and comparison criterion markers name only persisted finite item axes;
 * comparison post markers name only persisted finite person axes. Their accessible
 * names compose existing localized labels instead of creating a competing SPA
 * translation authority. Comparison graphic axes independently name persisted
 * finite, non-negative singular values and Gabriel inertia share. No coordinate,
 * singular value, share, distance, rank, or coverage is inferred from another field
 * or from rendered geometry. Click a post marker to open that post.
 *
 * Axis ticks name persisted leftover-map coordinates so ξ / ζ on the pair row match
 * the plot. Pair segments name persisted leftover-map distance ``d``, reconstruction
 * ``R̂``, explained leftover share ``e``, unexplained leftover share ``s``, cross
 * share ``x``, unexplained leftover ``U``, residual ``R``, observed ``Y``, expected
 * ``E``, and rank when their persisted evidence is usable. Coverage captions follow
 * the same fail-closed rule. Omit the plot when no pair has four finite leftover-map
 * coordinates. Never invent a leftover score or theta.
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
              aria-label={tf(LEFTOVER_MAP_PLOT_TICK, { axis: tick.axis, value: tick.label })}
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
                  aria-label={
                    variant === "comparison"
                      ? `${t(LEFTOVER_MAP_COMPARE_PLOT_LABEL)}: ${tf(LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE, {
                          label: segment.distanceLabel,
                        })}`
                      : tf(LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE, { label: segment.distanceLabel })
                  }
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
                  aria-label={
                    variant === "comparison"
                      ? `${t(LEFTOVER_MAP_COMPARE_PLOT_LABEL)}: ${tf(LEFTOVER_MAP_PLOT_SEGMENT_RANK, {
                          label: segment.rankLabel,
                        })}`
                      : tf(LEFTOVER_MAP_PLOT_SEGMENT_RANK, { label: segment.rankLabel })
                  }
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
          {layout.persons.map((marker) => (
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
          ))}
        </svg>
      </div>
    </figure>
  );
}
