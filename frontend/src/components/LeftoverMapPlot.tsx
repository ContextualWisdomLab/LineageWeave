import type { LeftoverMapAxis, LeftoverPair } from "../api";
import { t, tf } from "../i18n";
import { formatLeftoverMapCoordinatePair } from "../leftoverMapCoordinates";
import {
  formatLeftoverMapPlotAxisShare,
  leftoverShareForAxis,
  LEFTOVER_MAP_PLOT_AXIS_SHARE,
} from "../leftoverMapPlotAxisShare";
import {
  firstPlottablePairForPost,
  layoutLeftoverMapPlot,
  LEFTOVER_MAP_PLOT_CAPTION,
  LEFTOVER_MAP_PLOT_POST_ACTION,
  LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE,
  LEFTOVER_MAP_PLOT_SEGMENT_RECONSTRUCTION,
  LEFTOVER_MAP_PLOT_TICK,
} from "../leftoverMapPlotLayout";
import "./LeftoverMapPlot.css";

export type LeftoverMapPlotProps = {
  pairs: LeftoverPair[];
  leftoverMapAxes?: LeftoverMapAxis[];
  criterionLabel: (criterionCode: string) => string;
  onSelectPost: (pair: LeftoverPair) => void;
};

function diamondPoints(x: number, y: number, radius: number): string {
  return `${x},${y - radius} ${x + radius},${y} ${x},${y + radius} ${x - radius},${y}`;
}

function leftoverMapPlotAxisText(
  axisIndex: 1 | 2,
  leftoverMapAxes: LeftoverMapAxis[] | undefined,
): string {
  const percent = formatLeftoverMapPlotAxisShare(
    leftoverShareForAxis(leftoverMapAxes, axisIndex),
  );
  if (percent === null) {
    return t(axisIndex === 1 ? "leftover-map axis 1" : "leftover-map axis 2");
  }
  return tf(LEFTOVER_MAP_PLOT_AXIS_SHARE, { axis: axisIndex, share: percent });
}

/**
 * Gabriel leftover-map graphic display of persisted ``ξ_{1:2}`` / ``ζ_{1:2}``.
 *
 * Person markers are posts; item markers are leftover criteria. Click a
 * post marker to open that post. Caption leftover-map axes with persisted
 * Gabriel inertia share when finite, including rank-0 zero-share axes.
 * Axis ticks name persisted leftover-map coordinates so ξ / ζ on the
 * pair row match the plot. Pair segments name persisted leftover-map
 * distance ``d`` and leftover-map reconstruction ``R̂`` so the pair-row
 * badges match the graphic. Omit that distance caption when ``d`` is
 * missing or non-finite. Omit that reconstruction caption when ``R̂``
 * is missing or non-finite. Omit that axis
 * badge when share is missing or non-finite and keep the existing
 * leftover-map axis text. Omit the plot when no pair has four finite
 * leftover-map coordinates. Never invent a leftover score.
 */
export function LeftoverMapPlot({
  pairs,
  leftoverMapAxes,
  criterionLabel,
  onSelectPost,
}: LeftoverMapPlotProps) {
  const layout = layoutLeftoverMapPlot(pairs, criterionLabel);
  if (layout === null) {
    return null;
  }

  const openPost = (postId: string) => {
    const pair = firstPlottablePairForPost(pairs, postId);
    if (pair) {
      onSelectPost(pair as LeftoverPair);
    }
  };

  return (
    <figure className="leftover-map-plot" aria-label={t("Leftover-map graphic display")}>
      <figcaption className="leftover-map-plot-caption">{t(LEFTOVER_MAP_PLOT_CAPTION)}</figcaption>
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
          aria-label={t("Leftover map")}
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
            {leftoverMapPlotAxisText(1, leftoverMapAxes)}
          </text>
          <text className="leftover-map-plot-axis-label" x={layout.originX + 8} y={16}>
            {leftoverMapPlotAxisText(2, leftoverMapAxes)}
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
                  aria-label={tf(LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE, {
                    label: segment.distanceLabel,
                  })}
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
                  aria-label={tf(LEFTOVER_MAP_PLOT_SEGMENT_RECONSTRUCTION, {
                    label: segment.reconstructionLabel,
                  })}
                >
                  {segment.reconstructionLabel}
                </text>
              ) : null}
            </g>
          ))}
          {layout.items.map((marker) => (
            <g key={`item:${marker.id}`} aria-label={`${t("Criterion ζ")} ${marker.label}`}>
              <polygon className="leftover-map-plot-item" points={diamondPoints(marker.x, marker.y, 7)} />
              <text className="leftover-map-plot-label" x={marker.x + 10} y={marker.y + 14}>
                {marker.label}
              </text>
            </g>
          ))}
          {layout.persons.map((marker) => {
            const person = formatLeftoverMapCoordinatePair(marker.axis1, marker.axis2) ?? "";
            return (
              <g
                key={`person:${marker.id}`}
                className="leftover-map-plot-marker"
                role="button"
                tabIndex={0}
                aria-label={tf(LEFTOVER_MAP_PLOT_POST_ACTION, {
                  title: marker.label,
                  person,
                })}
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
