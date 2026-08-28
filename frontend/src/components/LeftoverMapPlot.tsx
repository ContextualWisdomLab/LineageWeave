import type { LeftoverPair } from "../api";
import { t, tf } from "../i18n";
import { formatLeftoverMapCoordinatePair } from "../leftoverMapCoordinates";
import {
  firstPlottablePairForPost,
  layoutLeftoverMapPlot,
  LEFTOVER_MAP_PLOT_CAPTION,
  LEFTOVER_MAP_PLOT_POST_ACTION,
} from "../leftoverMapPlotLayout";
import "./LeftoverMapPlot.css";

export type LeftoverMapPlotProps = {
  pairs: LeftoverPair[];
  criterionLabel: (criterionCode: string) => string;
  onSelectPost: (pair: LeftoverPair) => void;
};

function diamondPoints(x: number, y: number, radius: number): string {
  return `${x},${y - radius} ${x + radius},${y} ${x},${y + radius} ${x - radius},${y}`;
}

/**
 * Gabriel leftover-map graphic display of persisted ``ξ_{1:2}`` / ``ζ_{1:2}``.
 *
 * Person markers are posts; item markers are leftover criteria. Click a
 * post marker to open that post. Omit the plot when no pair has four
 * finite leftover-map coordinates. Never invent a leftover score.
 */
export function LeftoverMapPlot({
  pairs,
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
          role="img"
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
            {t("leftover-map axis 1")}
          </text>
          <text className="leftover-map-plot-axis-label" x={layout.originX + 8} y={16}>
            {t("leftover-map axis 2")}
          </text>
          {layout.segments.map((segment) => (
            <line
              key={`${segment.pairKind}:${segment.postId}:${segment.criterionCode}`}
              className={`leftover-map-plot-segment ${segment.pairKind}`}
              x1={segment.x1}
              y1={segment.y1}
              x2={segment.x2}
              y2={segment.y2}
            />
          ))}
          {layout.items.map((marker) => (
            <g key={`item:${marker.id}`} aria-label={`${t("Criterion ζ")} ${marker.label}`}>
              <polygon className="leftover-map-plot-item" points={diamondPoints(marker.x, marker.y, 7)} />
              <text className="leftover-map-plot-label" x={marker.x + 10} y={marker.y - 8}>
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
                <text className="leftover-map-plot-label" x={marker.x + 10} y={marker.y + 4}>
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
