import type { LeftoverPair, LineageGraph } from "./api";
import { leftoverBadgeText, leftoverPairsForPost } from "./leftoverCaption";
import { layoutLineageDag } from "./lineageLayout";

function truncateLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 33)}…` : label;
}

export function LineageDag({
  graph,
  onSelectPost,
  leftoverPairs,
}: {
  graph: LineageGraph;
  onSelectPost: (postId: string) => void;
  leftoverPairs?: LeftoverPair[];
}) {
  const groups = layoutLineageDag(graph);
  if (graph.nodes.length === 0) {
    return <p className="lineage-empty">No reconstructed lineage yet. Rebuild after seeding posts.</p>;
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
                return (
                  <path
                    key={`${edge.source}-${edge.target}`}
                    className="lineage-dag-edge"
                    d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                  >
                    <title>{`${from.label} → ${to.label} (${edge.fused_score.toFixed(2)})`}</title>
                  </path>
                );
              })}
              {group.nodes.map((node) => {
                const kind = node.is_branch_point ? "branch" : node.is_root ? "root" : "node";
                const leftoverForNode = leftoverPairsForPost(leftoverPairs, node.id);
                const leftoverTitles = leftoverForNode.map(leftoverBadgeText);
                return (
                  <g
                    key={node.id}
                    className={`lineage-dag-node lineage-dag-${kind}`}
                    transform={`translate(${node.x}, ${node.y})`}
                    role="button"
                    tabIndex={0}
                    aria-label={`Open post: ${node.label}`}
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
                    {leftoverForNode.map((pair, index) => (
                      <text
                        key={`${pair.pair_kind}:${pair.criterion_code}`}
                        className="lineage-dag-leftover"
                        x={12}
                        y={16 + index * 12}
                      >
                        {leftoverBadgeText(pair)}
                      </text>
                    ))}
                    <title>
                      {leftoverTitles.length > 0
                        ? `${node.label} — ${node.occurred_at.slice(0, 10)} — ${leftoverTitles.join(" · ")}`
                        : `${node.label} — ${node.occurred_at.slice(0, 10)}`}
                    </title>
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
