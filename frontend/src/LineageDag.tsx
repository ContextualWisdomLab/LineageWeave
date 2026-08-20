import type { LineageGraph, LineageGraphEdge, LineageGraphNode } from "./api";
import { t, tf } from "./i18n";
import { lineageEvidenceText } from "./lineageEvidenceI18n";
import { layoutLineageDag } from "./lineageLayout";
import "./LineageDag.css";

function truncateLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 33)}…` : label;
}

function exactScore(value: number | undefined): string {
  return value === undefined
    ? lineageEvidenceText("notAvailable")
    : value.toFixed(4);
}

function edgeEvidenceDescription(
  edge: LineageGraphEdge,
  from: LineageGraphNode,
  to: LineageGraphNode,
): string {
  const channelScores = edge.channel_scores ?? {};
  const parts = [
    `${lineageEvidenceText("fused")} ${exactScore(edge.fused_score)}`,
  ];
  if (channelScores.temporal !== undefined) {
    parts.push(
      `${lineageEvidenceText("time")} ${exactScore(channelScores.temporal)}`,
    );
  }
  if (channelScores.secondary_key !== undefined) {
    parts.push(
      `${lineageEvidenceText("secondaryKey")} ${exactScore(channelScores.secondary_key)}`,
    );
  }
  if (channelScores.text !== undefined) {
    parts.push(
      `${lineageEvidenceText("text")} ${exactScore(channelScores.text)}`,
    );
  }
  if (channelScores.llm !== undefined) {
    parts.push(
      `${lineageEvidenceText("llm")} ${exactScore(channelScores.llm)}`,
    );
  }
  return tf("{from} follows {to} ({score})", {
    from: from.label,
    to: to.label,
    score: parts.join("; "),
  });
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
    return (
      <p className="lineage-empty">
        {t("No reconstructed lineage yet. Rebuild after seeding posts.")}
      </p>
    );
  }

  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));

  return (
    <div className="lineage-dag" aria-label={t("Reconstructed lineage")}>
      {groups.map((group) => {
        const byId = Object.fromEntries(
          group.nodes.map((node) => [node.id, node]),
        );
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
                return (
                  <path
                    key={`${edge.source}-${edge.target}`}
                    className="lineage-dag-edge"
                    d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                  >
                    <title>{edgeEvidenceDescription(edge, from, to)}</title>
                  </path>
                );
              })}
              {group.nodes.map((node) => {
                const kind = node.is_branch_point
                  ? "branch"
                  : node.is_root
                    ? "root"
                    : "node";
                const isCurrent = node.id === currentPostId;
                return (
                  <g
                    key={node.id}
                    className={`lineage-dag-node lineage-dag-${kind}`}
                    transform={`translate(${node.x}, ${node.y})`}
                    role="button"
                    tabIndex={0}
                    aria-label={tf("Open post: {label}", {
                      label: node.label,
                    })}
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
      {graph.edges.length > 0 ? (
        <section className="popup-section" aria-labelledby="lineage-evidence-heading">
          <h3 id="lineage-evidence-heading">
            {lineageEvidenceText("whyLinked")}
          </h3>
          <p className="post-meta">{lineageEvidenceText("nextAction")}</p>
          <div className="lineage-evidence-scroll">
            <table
              className="lineage-evidence-table"
              aria-label={lineageEvidenceText("tableLabel")}
            >
              <thead>
                <tr>
                  <th scope="col">{lineageEvidenceText("from")}</th>
                  <th scope="col">{lineageEvidenceText("to")}</th>
                  <th scope="col">{lineageEvidenceText("fused")}</th>
                  <th scope="col">{lineageEvidenceText("time")}</th>
                  <th scope="col">
                    {lineageEvidenceText("secondaryKey")}
                  </th>
                  <th scope="col">{lineageEvidenceText("text")}</th>
                  <th scope="col">{lineageEvidenceText("llm")}</th>
                </tr>
              </thead>
              <tbody>
                {graph.edges.map((edge) => {
                  const from = nodeById.get(edge.source);
                  const to = nodeById.get(edge.target);
                  const channels = edge.channel_scores ?? {};
                  return (
                    <tr key={`${edge.source}-${edge.target}`}>
                      <th scope="row">{from?.label ?? edge.source}</th>
                      <td>{to?.label ?? edge.target}</td>
                      <td>{exactScore(edge.fused_score)}</td>
                      <td>{exactScore(channels.temporal)}</td>
                      <td>{exactScore(channels.secondary_key)}</td>
                      <td>{exactScore(channels.text)}</td>
                      <td>{exactScore(channels.llm)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </div>
  );
}
