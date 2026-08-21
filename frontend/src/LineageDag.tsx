import { useMemo, useState } from "react";
import type { LineageChannelEvidence, LineageGraph, LineageGraphEdge } from "./api";
import { t, tf } from "./i18n";
import { layoutLineageDag } from "./lineageLayout";

function truncateLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 33)}…` : label;
}

function edgeKey(edge: LineageGraphEdge): string {
  return `${edge.source}:${edge.target}`;
}

function formatExact(value: number): string {
  return value.toFixed(6);
}

function llmParticipated(evidence: LineageChannelEvidence[]): boolean {
  return evidence.some((item) => item.signal_code === "llm");
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
  const labelById = useMemo(
    () => Object.fromEntries(graph.nodes.map((node) => [node.id, node.label])),
    [graph.nodes],
  );
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);

  if (graph.nodes.length === 0) {
    return <p className="lineage-empty">{t("No reconstructed lineage yet. Rebuild after seeding posts.")}</p>;
  }

  return (
    <div className="lineage-dag" aria-label={t("Reconstructed lineage")}>
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
                const key = edgeKey(edge);
                const selected = selectedEdge === key;
                return (
                  <path
                    key={key}
                    className={selected ? "lineage-dag-edge lineage-dag-edge-selected" : "lineage-dag-edge"}
                    d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                    role="button"
                    tabIndex={0}
                    aria-label={tf("Open connection evidence: {from} to {to}", {
                      from: from.label,
                      to: to.label,
                    })}
                    onClick={() => setSelectedEdge(key)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedEdge(key);
                      }
                    }}
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
          </figure>
        );
      })}
      <section className="lineage-edge-evidence" aria-label={t("Connection evidence")}>
        <h3>{t("Connection evidence")}</h3>
        <p>
          {t("Each connection is inferred from independent signals. It is not a causal claim.")}
        </p>
        {graph.reconstruction ? (
          <dl className="lineage-rebuild-profile">
            <div>
              <dt>{t("Reconstruction version")}</dt>
              <dd>{graph.reconstruction.reconstruction_version}</dd>
            </div>
            <div>
              <dt>{t("Generated at")}</dt>
              <dd>{graph.reconstruction.generated_at}</dd>
            </div>
            <div>
              <dt>{t("Active weight profile")}</dt>
              <dd>
                {graph.reconstruction.active_weights
                  .map((item) => `${t(signalLabel(item.signal_code))}: ${formatExact(item.signal_weight)}`)
                  .join(", ")}
              </dd>
            </div>
          </dl>
        ) : null}
        {graph.edges.map((edge) => {
          const key = edgeKey(edge);
          const evidence = edge.channel_evidence ?? [];
          const fromLabel = labelById[edge.source] ?? edge.source;
          const toLabel = labelById[edge.target] ?? edge.target;
          return (
            <details
              key={key}
              className="lineage-edge-evidence-item"
              open
              onToggle={(event) => {
                const details = event.currentTarget;
                if (details.open) {
                  setSelectedEdge(key);
                } else if (selectedEdge === key) {
                  setSelectedEdge(null);
                }
              }}
            >
              <summary>
                {tf("{from} follows {to}, fused score {score}", {
                  from: fromLabel,
                  to: toLabel,
                  score: formatExact(edge.fused_score),
                })}
              </summary>
              {evidence.length > 0 && !llmParticipated(evidence) ? (
                <p>{t("No LLM adjudication participated in this connection.")}</p>
              ) : null}
              {evidence.length > 0 ? (
                <table>
                  <caption>{t("Connection evidence")}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{t("Rank")}</th>
                      <th scope="col">{t("Signal")}</th>
                      <th scope="col">{t("Score")}</th>
                      <th scope="col">{t("Weight")}</th>
                      <th scope="col">{t("Contribution")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evidence.map((item) => (
                      <tr key={item.signal_code}>
                        <td>{item.rank}</td>
                        <td>{t(item.signal_label)}</td>
                        <td>{formatExact(item.score)}</td>
                        <td>{formatExact(item.weight)}</td>
                        <td>{formatExact(item.contribution)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
            </details>
          );
        })}
      </section>
    </div>
  );
}

function signalLabel(signalCode: string): string {
  switch (signalCode) {
    case "temporal":
      return "Temporal proximity";
    case "secondary_key":
      return "Secondary key match";
    case "text":
      return "Text similarity";
    case "llm":
      return "LLM adjudication";
    default:
      return signalCode;
  }
}
