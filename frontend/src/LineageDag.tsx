import type { LineageGraph } from "./api";
import { layoutLineageDag } from "./lineageLayout";

function truncateLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 33)}…` : label;
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
    return <p className="lineage-empty">연결된 사건이 없습니다</p>;
  }

  return (
    <div className="lineage-dag" aria-label="Reconstructed lineage">
      {groups.map((group) => {
        const byId = Object.fromEntries(group.nodes.map((node) => [node.id, node]));
        return (
          <figure key={group.group} className="lineage-dag-group">
            <figcaption>
              {group.heading} ({group.nodes.length} records, {group.edges.length} lineage edges)
            </figcaption>
            <svg
              viewBox={`0 0 ${group.width} ${group.height}`}
              width="100%"
              height={Math.max(120, group.height)}
              role="img"
              aria-label={`${group.heading} lineage`}
            >
              {group.edges.map((edge) => {
                const from = byId[edge.source];
                const to = byId[edge.target];
                if (!from || !to) return null;
                const midX = (from.x + to.x) / 2;
                const midY = (from.y + to.y) / 2;
                const joinLabel =
                  edge.join_keys && edge.join_keys.length > 0
                    ? edge.join_keys.map((key) => key.label).join(" · ")
                    : edge.empty_next_action ?? "";
                const nextId = currentPostId === edge.source ? edge.target : edge.source;
                return (
                  <g key={`${edge.source}-${edge.target}`}>
                    <path
                      className="lineage-dag-edge"
                      d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                      role="button"
                      tabIndex={0}
                      aria-label={`Open linked post via ${joinLabel || "lineage edge"}`}
                      onClick={() => onSelectPost(nextId)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onSelectPost(nextId);
                        }
                      }}
                    >
                      <title>{`${from.label} → ${to.label}${joinLabel ? ` (${joinLabel})` : ""}`}</title>
                    </path>
                    {joinLabel ? (
                      <text className="lineage-dag-edge-label" x={midX} y={midY - 6} textAnchor="middle">
                        {joinLabel}
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
                    aria-label={`Open post: ${node.label}`}
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
                    <title>{`${node.label} — ${node.occurred_at.slice(0, 10)}`}</title>
                  </g>
                );
              })}
            </svg>
          </figure>
        );
      })}
    </div>
  );
}
