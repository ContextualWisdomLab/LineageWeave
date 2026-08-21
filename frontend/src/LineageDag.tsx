import type { LineageGraph } from "./api";
import { t, tf } from "./i18n";
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
    return <p className="lineage-empty">{t("No reconstructed lineage yet. Rebuild after seeding posts.")}</p>;
  }

  return (
    <div className="lineage-dag" aria-label={t("Reconstructed lineage")}>
      <div className="lineage-dag-header">
        <p className="section-eyebrow">BUYER EVIDENCE</p>
        <p className="lineage-dag-description">
          {t("Reconstructed lineage")}. {t("Edges explain reconstructed continuation only. They are not causal or authoritative facts.")}
        </p>
      </div>
      <div className="lineage-dag-legend" aria-label={t("Lineage legend")}>
        <span className="lineage-dag-legend-item">
          <span className="lineage-dag-legend-mark lineage-dag-legend-root" aria-hidden="true" />
          {t("Root record")}
        </span>
        <span className="lineage-dag-legend-item">
          <span className="lineage-dag-legend-mark lineage-dag-legend-branch" aria-hidden="true" />
          {t("Branch point")}
        </span>
        <span className="lineage-dag-legend-item">
          <span className="lineage-dag-legend-mark lineage-dag-legend-current" aria-hidden="true" />
          {t("Current record")}
        </span>
        <span className="lineage-dag-legend-item">→ {t("Parent to child")}</span>
      </div>
      {groups.map((group) => {
        const byId = Object.fromEntries(group.nodes.map((node) => [node.id, node]));
        return (
          <figure key={group.group} className="lineage-dag-group">
            <figcaption>
              {tf("{group} ({records} records, {edges} lineage edges)", {
                group: group.heading,
                records: group.nodes.length,
                edges: group.edges.length,
              })}
            </figcaption>
            <div className="lineage-dag-viewport">
              <svg
                viewBox={`0 0 ${group.width} ${group.height}`}
                width="100%"
                height={Math.max(120, group.height)}
                role="img"
                aria-label={tf("{group} lineage", { group: group.heading })}
              >
                <defs>
                  <marker id="lineage-dag-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                    <path d="M 0 0 L 8 4 L 0 8 z" fill="currentColor" />
                  </marker>
                </defs>
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
                      <title>
                        {tf("{from} follows {to} ({score})", {
                          from: from.label,
                          to: to.label,
                          score: edge.fused_score.toFixed(2),
                        })}
                      </title>
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
            </div>
          </figure>
        );
      })}
      <aside className="lineage-dag-inference-note">
        <strong>{t("Inference boundary")}</strong>
        {t("Edges explain reconstructed continuation only. They are not causal or authoritative facts.")}
      </aside>
      <section className="lineage-dag-evidence" aria-label={t("Evidence trail")}>
        <h4>{t("Evidence trail")}</h4>
        <table aria-label={t("Evidence trail")}>
          <thead>
            <tr>
              <th>{t("Graph relation")}</th>
              <th>{t("When")}</th>
              <th>{t("Evidence (fused_score)")}</th>
            </tr>
          </thead>
          <tbody>
            {groups.flatMap((group) =>
              group.edges.map((edge) => {
                const from = group.nodes.find((node) => node.id === edge.source);
                const to = group.nodes.find((node) => node.id === edge.target);
                if (!from || !to) return null;
                return (
                  <tr key={`${group.group}:${edge.source}:${edge.target}`}>
                    <td>{from.label} → {to.label}</td>
                    <td>{to.occurred_at.slice(0, 10)}</td>
                    <td>{edge.fused_score.toFixed(2)}</td>
                  </tr>
                );
              }),
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
