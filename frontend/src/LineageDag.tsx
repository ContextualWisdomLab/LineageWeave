import type {
  LineageChannelEvidence,
  LineageGraph,
  LineageGraphEdge,
  LineageGraphNode,
} from "./api";
import { t, tf } from "./i18n";
import { lineageEvidenceText } from "./lineageEvidenceI18n";
import { layoutLineageDag } from "./lineageLayout";
import "./LineageDag.css";

function truncateLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 33)}…` : label;
}

function exactScore(value: number | null | undefined): string {
  return value === undefined || value === null
    ? lineageEvidenceText("notAvailable")
    : value.toFixed(4);
}

function legacySignalLabel(signalCode: keyof NonNullable<LineageGraphEdge["channel_scores"]>): string {
  const keyBySignal = {
    temporal: "time",
    secondary_key: "secondaryKey",
    text: "text",
    llm: "llm",
  } as const;
  return lineageEvidenceText(keyBySignal[signalCode]);
}

function edgeEvidenceDescription(
  edge: LineageGraphEdge,
  from: LineageGraphNode,
  to: LineageGraphNode,
): string {
  const parts = [
    `${lineageEvidenceText("fused")} ${exactScore(edge.fused_score)}`,
  ];
  const evidence = edge.channel_evidence ?? [];
  if (evidence.length > 0) {
    for (const item of evidence) {
      parts.push(
        `${item.signal_label} ${exactScore(item.score)} × ${exactScore(item.weight)} = ${exactScore(item.contribution)}`,
      );
    }
  } else {
    for (const [signalCode, score] of Object.entries(
      edge.channel_scores ?? {},
    ) as [keyof NonNullable<LineageGraphEdge["channel_scores"]>, number][]) {
      parts.push(`${legacySignalLabel(signalCode)} ${exactScore(score)}`);
    }
  }
  return tf("{from} follows {to} ({score})", {
    from: from.label,
    to: to.label,
    score: parts.join("; "),
  });
}

function EvidenceTable({ evidence }: { evidence: LineageChannelEvidence[] }) {
  return (
    <div className="lineage-evidence-scroll">
      <table
        className="lineage-evidence-table"
        aria-label={lineageEvidenceText("tableLabel")}
      >
        <thead>
          <tr>
            <th scope="col">{lineageEvidenceText("rank")}</th>
            <th scope="col">{lineageEvidenceText("signal")}</th>
            <th scope="col">{lineageEvidenceText("score")}</th>
            <th scope="col">{lineageEvidenceText("weight")}</th>
            <th scope="col">{lineageEvidenceText("contribution")}</th>
          </tr>
        </thead>
        <tbody>
          {evidence.length > 0 ? (
            evidence.map((item) => (
              <tr key={item.signal_code}>
                <td>{item.rank}</td>
                <th scope="row">{item.signal_label}</th>
                <td>{exactScore(item.score)}</td>
                <td>{exactScore(item.weight)}</td>
                <td>{exactScore(item.contribution)}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={5}>{lineageEvidenceText("notAvailable")}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
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
          <p className="lineage-evidence-warning">
            {lineageEvidenceText("inferredNotice")}
          </p>
          <div className="lineage-evidence-disclosures">
            {graph.edges.map((edge) => {
              const from = nodeById.get(edge.source);
              const to = nodeById.get(edge.target);
              const evidence = edge.channel_evidence ?? [];
              const llmParticipated = evidence.some(
                (item) => item.signal_code === "llm",
              );
              return (
                <details
                  className="lineage-evidence-disclosure"
                  key={`${edge.source}-${edge.target}`}
                  open
                >
                  <summary>
                    {tf("{from} follows {to} ({score})", {
                      from: from?.label ?? edge.source,
                      to: to?.label ?? edge.target,
                      score: `${lineageEvidenceText("fused")} ${exactScore(edge.fused_score)}`,
                    })}
                  </summary>
                  <dl className="lineage-evidence-metadata">
                    <div>
                      <dt>{lineageEvidenceText("version")}</dt>
                      <dd>
                        {edge.reconstruction_version ??
                          lineageEvidenceText("notAvailable")}
                      </dd>
                    </div>
                    <div>
                      <dt>{lineageEvidenceText("generatedAt")}</dt>
                      <dd>
                        {edge.reconstructed_at ? (
                          <time dateTime={edge.reconstructed_at}>
                            {edge.reconstructed_at}
                          </time>
                        ) : (
                          lineageEvidenceText("notAvailable")
                        )}
                      </dd>
                    </div>
                  </dl>
                  {!llmParticipated ? (
                    <p className="post-meta">
                      {lineageEvidenceText("llmNotUsed")}
                    </p>
                  ) : null}
                  <EvidenceTable evidence={evidence} />
                </details>
              );
            })}
          </div>
        </section>
      ) : null}
    </div>
  );
}
