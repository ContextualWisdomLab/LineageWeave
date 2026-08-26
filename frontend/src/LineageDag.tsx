import { useMemo, useState } from "react";
import type { LineageChannelEvidence, LineageGraph, LineageGraphEdge } from "./api";
import { t, tf } from "./i18n";
import { layoutLineageDag } from "./lineageLayout";
import "./LineageDag.css";

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

function intervalLabel(edge: LineageGraphEdge): string | undefined {
  const label = edge.interval_relation_label?.trim();
  return label || undefined;
}

function otherPostId(edge: LineageGraphEdge, currentPostId?: string): string {
  if (currentPostId === edge.source) return edge.target;
  if (currentPostId === edge.target) return edge.source;
  return edge.target;
}

// Mirrors --size-control-min (24px, styles/tokens.css). One SVG user unit is
// ~1px here (see lineageLayout ROW_H/COL_W/PAD), so this radius gives the
// visible 7px node mark a 24x24px minimum hit area without CSS scale-up.
const NODE_HIT_RADIUS = 12;

/** Render the authorized lineage projection and let the reader open a post. */
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
        const labeledEdges = group.edges.filter((edge) => intervalLabel(edge) && byId[edge.source] && byId[edge.target]);
        const hasBranchPoint = group.nodes.some((node) => node.is_branch_point);
        return (
          <figure key={group.group} className="lineage-dag-group">
            <figcaption>
              {tf("{group} ({records} records, {edges} lineage edges)", {
                group: group.heading,
                records: group.nodes.length,
                edges: group.edges.length,
              })}
            </figcaption>
            {group.edges.length > 0 && !hasBranchPoint ? (
              <p className="lineage-dag-linear-note" role="note">
                {t(
                  "This chain has no branch point: each non-root record matched exactly one likely predecessor. See the evidence trail below for why each link was made.",
                )}
              </p>
            ) : null}
            <p className="lineage-dag-scroll-hint">
              {t("Swipe or use arrow keys to inspect the full lineage.")}
            </p>
            <div
              className="lineage-dag-viewport"
              role="region"
              tabIndex={0}
              aria-label={tf("{group} lineage viewport", { group: group.heading })}
            >
              <svg
                viewBox={`0 0 ${group.width} ${group.height}`}
                width={group.width}
                height={Math.max(120, group.height)}
                role="group"
                aria-label={tf("{group} lineage", { group: group.heading })}
              >
                {group.edges.map((edge) => {
                  const from = byId[edge.source];
                  const to = byId[edge.target];
                  const midX = (from.x + to.x) / 2;
                  const key = edgeKey(edge);
                  const selected = selectedEdge === key;
                  const relation = intervalLabel(edge);
                  return (
                    <g key={key}>
                      <path
                        className={selected ? "lineage-dag-edge lineage-dag-edge-selected" : "lineage-dag-edge"}
                        d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                        role="button"
                        tabIndex={0}
                        aria-pressed={selected}
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
                      <circle
                        className="lineage-dag-hit"
                        r={NODE_HIT_RADIUS}
                        fill="transparent"
                        style={{ pointerEvents: "all" }}
                      />
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
      <section className="lineage-edge-evidence" aria-label={t("Connection evidence")}>
        <h3>{t("Connection evidence")}</h3>
        <p>
          {t("Each connection is inferred from independent signals. It is not a causal claim.")}
        </p>
        {graph.reconstruction ? (
          <dl className="lineage-rebuild-profile">
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
        {groups.map((group) => (
          <section key={group.group} aria-label={group.heading}>
            <h4>{group.heading}</h4>
            {group.edges.map((edge) => {
              const key = edgeKey(edge);
              const evidence = edge.channel_evidence ?? [];
              const fromLabel = labelById[edge.source] ?? edge.source;
              const toLabel = labelById[edge.target] ?? edge.target;
              return (
            <details
              key={key}
              className="lineage-edge-evidence-item"
              open={selectedEdge === key}
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
                  from: toLabel,
                  to: fromLabel,
                  score: formatExact(edge.fused_score),
                })}
              </summary>
              {evidence.length > 0 && !llmParticipated(evidence) ? (
                <p>{t("No additional review signal was available for this connection. Open the related records to review the evidence.")}</p>
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
        ))}
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
      return "Additional review";
    default:
      return signalCode;
  }
}
