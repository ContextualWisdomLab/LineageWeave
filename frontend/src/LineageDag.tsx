import { useId } from "react";
import type { LineageGraph } from "./api";
import "./LineageDag.css";
import { t, tf } from "./i18n";
import { layoutLineageDag } from "./lineageLayout";

const NODE_RADIUS = 7;
const EDGE_CLEARANCE = 4;

interface Point {
  x: number;
  y: number;
}

function truncateLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 33)}…` : label;
}

function eventDate(occurredAt: string): string {
  return occurredAt.slice(0, 10);
}

function edgePath(from: Point, to: Point): string {
  const angle = Math.atan2(to.y - from.y, to.x - from.x);
  const offsetX = Math.cos(angle) * (NODE_RADIUS + EDGE_CLEARANCE);
  const offsetY = Math.sin(angle) * (NODE_RADIUS + EDGE_CLEARANCE);
  const startX = from.x + offsetX;
  const startY = from.y + offsetY;
  const endX = to.x - offsetX;
  const endY = to.y - offsetY;
  const midX = (startX + endX) / 2;
  return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
}

export function LineageDag({
  graph,
  onSelectPost,
  currentPostId,
}: {
  graph: LineageGraph;
  onSelectPost: (postId: string) => void;
  currentPostId?: string;
}) {
  const instanceId = useId().replaceAll(":", "");
  const groups = layoutLineageDag(graph);
  if (graph.nodes.length === 0) {
    return <p className="lineage-empty">{t("No reconstructed lineage yet. Rebuild after seeding posts.")}</p>;
  }

  return (
    <div className="lineage-dag" aria-label={t("Reconstructed lineage")}>
      {groups.map((group, groupIndex) => {
        const byId = Object.fromEntries(group.nodes.map((node) => [node.id, node]));
        const arrowMarkerId = `lineage-dag-arrow-${instanceId}-${groupIndex}`;
        const captionId = `lineage-dag-caption-${instanceId}-${groupIndex}`;
        const lineageLabel = tf("{group} lineage", { group: group.heading });
        return (
          <figure key={group.group} className="lineage-dag-group">
            <figcaption id={captionId}>
              {tf("{group} ({records} records, {edges} lineage edges)", {
                group: group.heading,
                records: group.nodes.length,
                edges: group.edges.length,
              })}
            </figcaption>
            <div
              className="lineage-dag-scroll"
              role="region"
              aria-labelledby={captionId}
              tabIndex={0}
            >
              <svg
                className="lineage-dag-canvas"
                viewBox={`0 0 ${group.width} ${group.height}`}
                width={group.width}
                height={Math.max(120, group.height)}
                role="group"
                aria-label={lineageLabel}
              >
                <defs>
                  <marker
                    id={arrowMarkerId}
                    markerWidth="8"
                    markerHeight="8"
                    refX="7"
                    refY="4"
                    orient="auto"
                    markerUnits="strokeWidth"
                  >
                    <path className="lineage-dag-arrow" d="M 0 0 L 8 4 L 0 8 z" />
                  </marker>
                </defs>
                {group.edges.map((edge) => {
                  const from = byId[edge.source];
                  const to = byId[edge.target];
                  if (!from || !to) return null;
                  return (
                    <path
                      key={`${edge.source}-${edge.target}`}
                      className="lineage-dag-edge"
                      markerEnd={`url(#${arrowMarkerId})`}
                      d={edgePath(from, to)}
                    >
                      <title>{`${from.label} → ${to.label} (${edge.fused_score.toFixed(2)})`}</title>
                    </path>
                  );
                })}
                {group.nodes.map((node) => {
                  const kind = node.is_branch_point ? "branch" : node.is_root ? "root" : "node";
                  const isCurrent = node.id === currentPostId;
                  return (
                    <g
                      key={node.id}
                      className={`lineage-dag-node lineage-dag-${kind}`}
                      transform={`translate(${node.x}, ${node.y})`}
                      role="button"
                      tabIndex={0}
                      aria-label={tf("Open post: {label}", { label: node.label })}
                      aria-current={isCurrent ? "true" : undefined}
                      onClick={() => onSelectPost(node.id)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onSelectPost(node.id);
                        }
                      }}
                    >
                      <circle r={NODE_RADIUS} />
                      <text x={12} y={1}>
                        {truncateLabel(node.label)}
                      </text>
                      <text className="lineage-dag-node-date" x={12} y={15}>
                        {eventDate(node.occurred_at)}
                      </text>
                      <title>
                        {tf("{label} — {date}", {
                          label: node.label,
                          date: eventDate(node.occurred_at),
                        })}
                      </title>
                    </g>
                  );
                })}
              </svg>
            </div>
            <details className="lineage-dag-evidence" open>
              <summary>{t("Evidence trail")}</summary>
              <div className="lineage-dag-evidence-scroll">
                <table className="lineage-dag-evidence-table">
                  <caption className="visually-hidden">{`${lineageLabel} — ${t("Evidence trail")}`}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{t("Graph relation")}</th>
                      <th scope="col">{t("When")}</th>
                      <th scope="col">{t("Evidence")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.edges.map((edge) => {
                      const from = byId[edge.source];
                      const to = byId[edge.target];
                      if (!from || !to) return null;
                      return (
                        <tr key={`${edge.source}-${edge.target}-evidence`}>
                          <td>{`${from.label} → ${to.label}`}</td>
                          <td>{`${eventDate(from.occurred_at)} → ${eventDate(to.occurred_at)}`}</td>
                          <td>{edge.fused_score.toFixed(2)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </details>
          </figure>
        );
      })}
    </div>
  );
}
