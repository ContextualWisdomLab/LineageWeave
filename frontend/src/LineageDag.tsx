import type { LineageGraph, LineageGraphEdge } from "./api";
import { t, tf } from "./i18n";
import { layoutLineageDag } from "./lineageLayout";

function truncateLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 33)}…` : label;
}

function intervalLabel(edge: LineageGraphEdge): string | undefined {
  const label = edge.interval_relation_label?.trim();
  return label || undefined;
}

function otherPostId(edge: LineageGraphEdge, currentPostId?: string): string {
  if (currentPostId === edge.source) return edge.target;
  if (currentPostId === edge.target) return edge.source;
  return edge.target;
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
  const groups = layoutLineageDag(graph);
  if (graph.nodes.length === 0) {
    return <p className="lineage-empty">{t("No reconstructed lineage yet. Rebuild after seeding posts.")}</p>;
  }

  return (
    <div className="lineage-dag" aria-label={t("Reconstructed lineage")}>
      {groups.map((group) => {
        const byId = Object.fromEntries(group.nodes.map((node) => [node.id, node]));
        const labeledEdges = group.edges.filter((edge) => intervalLabel(edge) && byId[edge.source] && byId[edge.target]);
        return (
          <figure key={group.group} className="lineage-dag-group">
            <figcaption>
              {tf("{group} ({records} records, {edges} lineage edges)", {
                group: group.heading,
                records: group.nodes.length,
                edges: group.edges.length,
              })}
            </figcaption>
            <svg
              viewBox={`0 0 ${group.width} ${group.height}`}
              width="100%"
              height={Math.max(120, group.height)}
              role="img"
              aria-label={tf("{group} lineage", { group: group.heading })}
            >
              {group.edges.map((edge) => {
                const from = byId[edge.source];
                const to = byId[edge.target];
                if (!from || !to) return null;
                const midX = (from.x + to.x) / 2;
                const midY = (from.y + to.y) / 2;
                const relation = intervalLabel(edge);
                return (
                  <g key={`${edge.source}-${edge.target}`}>
                    <path
                      className="lineage-dag-edge"
                      d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                    >
                      <title>
                        {relation
                          ? tf("{from} follows {to} ({score}) — {relation}", {
                              from: to.label,
                              to: from.label,
                              score: edge.fused_score.toFixed(2),
                              relation: t(relation),
                            })
                          : tf("{from} follows {to} ({score})", {
                              from: to.label,
                              to: from.label,
                              score: edge.fused_score.toFixed(2),
                            })}
                      </title>
                    </path>
                    {relation ? (
                      <text
                        className="lineage-dag-interval"
                        x={midX}
                        y={midY - 6}
                        textAnchor="middle"
                      >
                        {t(relation)}
                      </text>
                    ) : null}
                  </g>
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
                    <circle r={7} />
                    <text x={12} y={4}>
                      {truncateLabel(node.label)}
                    </text>
                    <title>
                      {tf("{label} — {date}", {
                        label: node.label,
                        date: node.occurred_at.slice(0, 10),
                      })}
                    </title>
                  </g>
                );
              })}
            </svg>
            {labeledEdges.length > 0 ? (
              <ul className="lineage-interval-list" aria-label={t("Interval relations")}>
                {labeledEdges.map((edge) => {
                  const from = byId[edge.source];
                  const to = byId[edge.target];
                  const openId = otherPostId(edge, currentPostId);
                  const openNode = byId[openId];
                  const relation = intervalLabel(edge);
                  if (!from || !to || !openNode || !relation) return null;
                  return (
                    <li key={`${edge.source}-${edge.target}`}>
                      <button
                        type="button"
                        className="lineage-interval-button"
                        onClick={() => onSelectPost(openNode.id)}
                        aria-label={tf("{from} relates to {to} as {relation}; open {label}", {
                          from: from.label,
                          to: to.label,
                          relation: t(relation),
                          label: openNode.label,
                        })}
                      >
                        <span className="lineage-interval-code">{t(relation)}</span>
                        <span>{tf("Open post: {label}", { label: openNode.label })}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </figure>
        );
      })}
    </div>
  );
}
