import { useId } from "react";
import type { LineageGraph } from "./api";
import "./LineageDag.css";
import { LINE_H } from "./graphLabel";
import { t, tf } from "./i18n";
import { lineageDagText } from "./lineageDagI18n";
import { layoutLineageDag, PAD } from "./lineageLayout";

const NODE_RADIUS = 7;
const MARK_EXTENT = 11;
const EDGE_CLEARANCE = 4;

interface Point {
  x: number;
  y: number;
}

function eventDate(occurredAt: string): string {
  return occurredAt.slice(0, 10);
}

/** Fixed display order matching reconstruct.DEFAULT_CHANNEL_WEIGHTS. */
const CHANNEL_ORDER = ["temporal", "secondary_key", "text", "llm"] as const;

function channelLabel(code: string): string {
  switch (code) {
    case "temporal":
      return lineageDagText("Temporal proximity");
    case "secondary_key":
      return lineageDagText("Secondary key match");
    case "text":
      return lineageDagText("Text similarity");
    case "llm":
      return lineageDagText("LLM judgment");
    default:
      // A channel this UI doesn't yet know how to label: show the raw code
      // rather than silently dropping evidence the backend actually sent.
      return code;
  }
}

/** ADR 0191: fused_score alone doesn't say WHY reconstruct linked two posts. */
function channelBreakdown(scores: Record<string, number>): string {
  const codes = Object.keys(scores);
  const ordered = CHANNEL_ORDER.filter((code) => codes.includes(code));
  const remaining = codes.filter((code) => !(CHANNEL_ORDER as readonly string[]).includes(code));
  return [...ordered, ...remaining]
    .map((code) => `${channelLabel(code)} ${scores[code].toFixed(2)}`)
    .join(" · ");
}

function edgePath(from: Point, to: Point): string {
  const angle = Math.atan2(to.y - from.y, to.x - from.x);
  const offsetX = Math.cos(angle) * (MARK_EXTENT + EDGE_CLEARANCE);
  const offsetY = Math.sin(angle) * (MARK_EXTENT + EDGE_CLEARANCE);
  const startX = from.x + offsetX;
  const startY = from.y + offsetY;
  const endX = to.x - offsetX;
  const endY = to.y - offsetY;
  const midX = (startX + endX) / 2;
  return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
}

function wrapTspans(lines: string[], x: number, lineHeight: number) {
  return lines.map((line, index) => (
    <tspan key={index} x={x} dy={index === 0 ? 0 : lineHeight}>
      {index < lines.length - 1 ? `${line} ` : line}
    </tspan>
  ));
}

function NodeMark({ kind, isCurrent }: { kind: "root" | "branch" | "node"; isCurrent: boolean }) {
  return (
    <>
      {isCurrent ? <circle className="lineage-dag-current-ring" r={11} /> : null}
      {kind === "root" ? (
        <rect className="lineage-dag-mark" x={-7} y={-7} width={14} height={14} rx={2} />
      ) : kind === "branch" ? (
        <polygon className="lineage-dag-mark" points="0,-9 9,0 0,9 -9,0" />
      ) : (
        <circle className="lineage-dag-mark" r={NODE_RADIUS} />
      )}
    </>
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
  const instanceId = useId().replaceAll(":", "");
  const groups = layoutLineageDag(graph);
  if (graph.nodes.length === 0) {
    return (
      <p className="lineage-empty">
        {lineageDagText(
          "No reconstructed lineage yet. Add eligible source records, then rebuild Event Lineage.",
        )}
      </p>
    );
  }

  return (
    <div className="lineage-dag" aria-label={t("Reconstructed lineage")}>
      <div className="lineage-dag-header">
        <p className="section-eyebrow">{t("Lineage evidence")}</p>
        <p className="lineage-dag-description">
          {t("Reconstructed lineage")}. {t("Edges explain reconstructed continuation only. They are not causal or authoritative facts.")}
        </p>
      </div>
      <ul className="lineage-dag-legend" aria-label={lineageDagText("Lineage legend")}>
        <li className="lineage-dag-legend-item">
          <span
            className="lineage-dag-legend-node lineage-dag-legend-mark lineage-dag-legend-root"
            aria-hidden="true"
          />
          {lineageDagText("Root record")}
        </li>
        <li className="lineage-dag-legend-item">
          <span
            className="lineage-dag-legend-node lineage-dag-legend-mark lineage-dag-legend-branch"
            aria-hidden="true"
          />
          {lineageDagText("Branch point")}
        </li>
        <li className="lineage-dag-legend-item">
          <span
            className="lineage-dag-legend-node lineage-dag-legend-mark lineage-dag-legend-current"
            aria-hidden="true"
          />
          {lineageDagText("Current record")}
        </li>
        <li className="lineage-dag-legend-item">
          <span className="lineage-dag-legend-direction" aria-hidden="true" />
          {lineageDagText("Parent to child")}
        </li>
        <li className="lineage-dag-legend-item">
          <span className="lineage-dag-legend-direction" aria-hidden="true" />
          {lineageDagText("Predecessor to successor")}
        </li>
      </ul>
      {groups.map((group, groupIndex) => {
        const byId = Object.fromEntries(group.nodes.map((node) => [node.id, node]));
        const hasBranchPoint = group.nodes.some((node) => node.is_branch_point);
        const arrowMarkerId = `lineage-dag-arrow-${instanceId}-${groupIndex}`;
        const captionId = `lineage-dag-caption-${instanceId}-${groupIndex}`;
        const lineageLabel = tf("{group} lineage", { group: group.heading });
        const relationLabel = t("Graph relation");
        const whenLabel = t("When");
        const breakdownLabel = lineageDagText("Channel breakdown");
        const evidenceLabel = `${t("Evidence")} (fused_score)`;
        return (
          <figure key={group.group} className="lineage-dag-group">
            <figcaption id={captionId}>
              {`${lineageDagText("Topic")} ${tf("{group} ({records} records, {edges} lineage edges)", {
                group: group.heading,
                records: group.nodes.length,
                edges: group.edges.length,
              })}`}
            </figcaption>
            <div
              className="lineage-dag-scroll lineage-dag-viewport"
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
                <text className="lineage-dag-topic" x={PAD} y={16}>
                  {`${lineageDagText("Topic")}: ${group.heading}`}
                </text>
                <text className="lineage-dag-axis" x={PAD} y={32}>
                  {lineageDagText("Earlier")}
                </text>
                <text className="lineage-dag-axis" x={group.width / 2} y={32} textAnchor="middle">
                  {`${lineageDagText("Predecessor to successor")} · ${lineageDagText("Parent to child")}`}
                </text>
                <text className="lineage-dag-axis" x={group.width - PAD} y={32} textAnchor="end">
                  {lineageDagText("Later")}
                </text>
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
                  // Root/branch/current are otherwise conveyed by stroke color and
                  // border width alone (see .lineage-dag-root/-branch/[aria-current]
                  // in App.css) — name them here too so the distinction reaches
                  // screen readers and colorblind users relying on the tooltip.
                  const kindLabels = [
                    isCurrent ? lineageDagText("Current record") : null,
                    kind === "branch" ? lineageDagText("Branch point") : null,
                    kind === "root" ? lineageDagText("Root record") : null,
                  ].filter((label): label is string => Boolean(label));
                  const kindSuffix = kindLabels.length > 0 ? ` (${kindLabels.join(", ")})` : "";
                  const dateY = node.labelLines.length * LINE_H + 4;
                  const kindY = dateY + 12;
                  return (
                    <g
                      key={node.id}
                      className={`lineage-dag-node lineage-dag-${kind}`}
                      transform={`translate(${node.x}, ${node.y})`}
                      role="button"
                      tabIndex={0}
                      aria-label={tf("Open post: {label}", { label: node.label }) + kindSuffix}
                      aria-current={isCurrent ? "true" : undefined}
                      onClick={() => onSelectPost(node.id)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onSelectPost(node.id);
                        }
                      }}
                    >
                      <NodeMark kind={kind} isCurrent={isCurrent} />
                      <text className="lineage-dag-node-label" x={12} y={1}>
                        {wrapTspans(node.labelLines, 12, LINE_H)}
                      </text>
                      <text className="lineage-dag-node-date" x={12} y={dateY}>
                        {eventDate(node.occurred_at)}
                      </text>
                      {kindLabels.length > 0 ? (
                        <text className="lineage-dag-node-kind" x={12} y={kindY}>
                          {kindLabels.join(" · ")}
                        </text>
                      ) : null}
                      <title>
                        {tf("{label} — {date}", {
                          label: node.label,
                          date: eventDate(node.occurred_at),
                        }) + kindSuffix}
                      </title>
                    </g>
                  );
                })}
              </svg>
            </div>
            {group.edges.length > 0 ? (
              <>
                {!hasBranchPoint ? (
                  <p className="lineage-dag-boundary lineage-dag-linear-note" role="note">
                    {lineageDagText(
                      "This chain has no branch point: each record matched exactly one likely predecessor. See the evidence trail below for why each link was made.",
                    )}
                  </p>
                ) : null}
                <p className="lineage-dag-boundary lineage-dag-inference-note" role="note">
                  <strong>{t("Inference boundary")}</strong>{" "}
                  {lineageDagText(
                    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.",
                  )}
                </p>
                <details className="lineage-dag-evidence" open>
                  <summary>{t("Evidence trail")}</summary>
                  <div className="lineage-dag-evidence-scroll">
                    <table className="lineage-dag-evidence-table">
                      <caption className="visually-hidden">{`${lineageLabel} — ${t("Evidence trail")}`}</caption>
                      <thead>
                        <tr>
                          <th scope="col">{relationLabel}</th>
                          <th scope="col">{whenLabel}</th>
                          <th scope="col">{evidenceLabel}</th>
                          <th scope="col">{breakdownLabel}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {group.edges.map((edge) => {
                          const from = byId[edge.source];
                          const to = byId[edge.target];
                          if (!from || !to) return null;
                          return (
                            <tr key={`${edge.source}-${edge.target}-evidence`}>
                              <td data-label={relationLabel}>{`${from.label} → ${to.label}`}</td>
                              <td data-label={whenLabel}>{`${eventDate(from.occurred_at)} → ${eventDate(to.occurred_at)}`}</td>
                              <td data-label={evidenceLabel}>{edge.fused_score.toFixed(2)}</td>
                              <td data-label={breakdownLabel}>{channelBreakdown(edge.channel_scores)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </details>
              </>
            ) : null}
          </figure>
        );
      })}
    </div>
  );
}
