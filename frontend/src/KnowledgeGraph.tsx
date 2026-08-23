import { useId, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import type { KnowledgeGraph, KnowledgeGraphNode } from "./api";
import { CHAR_W, KNOWLEDGE_LABEL_CHARS, LINE_H, wrapLabel } from "./graphLabel";
import { t, tf } from "./i18n";
import "./KnowledgeGraph.css";

const MIN_NODE_W = 200;
const MIN_ZOOM = 0.75;
const MAX_ZOOM = 2.5;
const ZOOM_STEP = 1.2;

type GraphView = { scale: number; x: number; y: number };
type DragState = {
  pointerId: number;
  startX: number;
  startY: number;
  startPanX: number;
  startPanY: number;
  svgWidth: number;
  svgHeight: number;
  moved: boolean;
};

type LaidOutNode = {
  x: number;
  y: number;
  width: number;
  height: number;
  lines: string[];
  typeLines: string[];
};

function wrapTspans(lines: string[], x: number, lineHeight: number) {
  return lines.map((line, index) => (
    <tspan key={index} x={x} dy={index === 0 ? 0 : lineHeight}>
      {index < lines.length - 1 ? `${line} ` : line}
    </tspan>
  ));
}

function nodeCaption(node: KnowledgeGraphNode): string {
  return node.is_evidence_text_node ? `${node.label} (${node.ontology_label ?? node.node_type_code})` : node.label;
}

function nodeBox(label: string, typeLabel: string): Omit<LaidOutNode, "x" | "y"> {
  const lines = wrapLabel(label, KNOWLEDGE_LABEL_CHARS);
  const typeLines = wrapLabel(typeLabel, KNOWLEDGE_LABEL_CHARS);
  const longest = Math.max(
    ...lines.map((line) => line.length),
    ...typeLines.map((line) => line.length),
    12,
  );
  return {
    lines,
    typeLines,
    width: Math.max(MIN_NODE_W, longest * CHAR_W + 24),
    height: Math.max(52, 16 + lines.length * LINE_H + typeLines.length * 12),
  };
}

function layoutKnowledgeGraph(graph: KnowledgeGraph): {
  positions: Map<string, LaidOutNode>;
  width: number;
  height: number;
} {
  const focus = graph.nodes.find((node) => node.is_focus);
  const others = graph.nodes.filter((node) => !node.is_focus);
  const boxes = new Map(
    graph.nodes.map((node) => {
      const caption = nodeCaption(node);
      const typeLabel = node.ontology_label ?? node.node_type_code;
      return [node.id, nodeBox(caption, typeLabel)] as const;
    }),
  );
  const rowPitch = Math.max(80, ...[...boxes.values()].map((box) => box.height + 16));
  const maxOtherWidth = Math.max(MIN_NODE_W, ...others.map((node) => boxes.get(node.id)!.width));
  const focusWidth = focus ? boxes.get(focus.id)!.width : MIN_NODE_W;
  const width = Math.max(760, maxOtherWidth * 2 + focusWidth + 80);
  const height = Math.max(260, (others.length + 1) * rowPitch);
  const positions = new Map<string, LaidOutNode>();
  if (focus) {
    const box = boxes.get(focus.id)!;
    positions.set(focus.id, { ...box, x: width / 2, y: height / 2 });
  }
  others.forEach((node, index) => {
    const box = boxes.get(node.id)!;
    const left = index % 2 === 0;
    const row = Math.floor(index / 2);
    positions.set(node.id, {
      ...box,
      x: left ? 16 + box.width / 2 : width - 16 - box.width / 2,
      y: 24 + box.height / 2 + row * rowPitch,
    });
  });
  return { positions, width, height };
}

function edgePath(from: LaidOutNode, to: LaidOutNode): string {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  const ux = dx / length;
  const uy = dy / length;
  const startX = from.x + ux * (from.width / 2);
  const startY = from.y + uy * (from.height / 2);
  const endX = to.x - ux * (to.width / 2);
  const endY = to.y - uy * (to.height / 2);
  return `M ${startX} ${startY} L ${endX} ${endY}`;
}

export function KnowledgeGraphView({
  graph,
  onSelectPost,
}: {
  graph: KnowledgeGraph;
  onSelectPost?: (postId: string) => void;
}) {
  const graphId = useId().replaceAll(":", "");
  const markerId = `knowledge-graph-arrow-${graphId}`;
  const titleId = `knowledge-graph-title-${graphId}`;
  const descriptionId = `knowledge-graph-description-${graphId}`;
  const instructionsId = `knowledge-graph-instructions-${graphId}`;
  const { positions, width, height } = layoutKnowledgeGraph(graph);
  const nodesById = new Map(graph.nodes.map((node) => [node.id, node]));
  const [view, setView] = useState<GraphView>({ scale: 1, x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<DragState | null>(null);
  const lastPanAtRef = useRef(0);

  const zoomAt = (factor: number, clientX?: number, clientY?: number) => {
    const svg = svgRef.current;
    setView((current) => {
      const nextScale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, current.scale * factor));
      if (nextScale === current.scale) return current;
      if (!svg) return { ...current, scale: nextScale };
      const rect = svg.getBoundingClientRect();
      const localX = clientX === undefined ? rect.width / 2 : clientX - rect.left;
      const localY = clientY === undefined ? rect.height / 2 : clientY - rect.top;
      const viewX = (localX / rect.width) * width;
      const viewY = (localY / rect.height) * height;
      const worldX = (viewX - current.x) / current.scale;
      const worldY = (viewY - current.y) / current.scale;
      return {
        scale: nextScale,
        x: viewX - worldX * nextScale,
        y: viewY - worldY * nextScale,
      };
    });
  };

  const panByKeyboard = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.target !== event.currentTarget) return;
    const delta = 40;
    const offset = {
      ArrowLeft: { x: delta, y: 0 },
      ArrowRight: { x: -delta, y: 0 },
      ArrowUp: { x: 0, y: delta },
      ArrowDown: { x: 0, y: -delta },
    }[event.key];
    if (!offset) return;
    event.preventDefault();
    setView((current) => ({ ...current, x: current.x + offset.x, y: current.y + offset.y }));
  };

  const beginPan = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    const rect = svgRef.current!.getBoundingClientRect();
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startPanX: view.x,
      startPanY: view.y,
      svgWidth: rect.width,
      svgHeight: rect.height,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const movePan = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const dx = (event.clientX - drag.startX) * (width / drag.svgWidth);
    const dy = (event.clientY - drag.startY) * (height / drag.svgHeight);
    if (Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) > 4) {
      drag.moved = true;
    }
    setView((current) => ({ ...current, x: drag.startPanX + dx, y: drag.startPanY + dy }));
  };

  const endPan = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (drag.moved) lastPanAtRef.current = Date.now();
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  return (
    <section className="knowledge-graph" aria-label={t("Knowledge Graph")}>
      <div className="knowledge-graph-header">
        <div>
          <p className="section-eyebrow">{t("Knowledge Graph")}</p>
          <p className="knowledge-graph-description">
            {t("Persisted edges and source-grounded semantic relations")}
          </p>
        </div>
        <div className="knowledge-graph-actions">
          {graph.truncated ? <span className="post-badge">{t("Limited view")}</span> : null}
          <div className="knowledge-graph-controls" role="group" aria-label={t("Graph controls")}>
            <button type="button" onClick={() => zoomAt(ZOOM_STEP)} aria-label={t("Zoom in")}>
              +
            </button>
            <span aria-live="polite">{Math.round(view.scale * 100)}%</span>
            <button type="button" onClick={() => zoomAt(1 / ZOOM_STEP)} aria-label={t("Zoom out")}>
              −
            </button>
            <button
              type="button"
              className="knowledge-graph-reset"
              onClick={() => setView({ scale: 1, x: 0, y: 0 })}
              aria-label={t("Reset graph view")}
            >
              {t("Reset")}
            </button>
          </div>
        </div>
      </div>
      {graph.nodes.length === 0 ? (
        <p className="popup-placeholder">{t("No Knowledge Graph evidence is available.")}</p>
      ) : (
        <>
          <p id={instructionsId} className="knowledge-graph-instructions">
            {t("Arrows show source → target; use arrow keys to pan and controls to zoom.")}
          </p>
          <div
            className="knowledge-graph-viewport"
            role="region"
            aria-label={t("Knowledge Graph")}
            aria-describedby={instructionsId}
            tabIndex={0}
            onKeyDown={panByKeyboard}
            onPointerDown={beginPan}
            onPointerMove={movePan}
            onPointerUp={endPan}
            onPointerCancel={endPan}
            onWheel={(event) => {
              event.preventDefault();
              zoomAt(event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP, event.clientX, event.clientY);
            }}
          >
            <svg
              ref={svgRef}
              viewBox={`0 0 ${width} ${height}`}
              width="100%"
              height={height}
              role="img"
              aria-labelledby={titleId}
              aria-describedby={descriptionId}
            >
              <title id={titleId}>{t("Knowledge Graph directed relations")}</title>
              <desc id={descriptionId}>
                {t("Arrows show source → target; use arrow keys to pan and controls to zoom.")}
              </desc>
              <defs>
                <marker id={markerId} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path className="knowledge-graph-arrow" d="M 0 0 L 8 4 L 0 8 z" />
                </marker>
              </defs>
              <g transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
                {graph.edges.map((edge, index) => {
                  const from = positions.get(edge.source);
                  const to = positions.get(edge.target);
                  if (!from || !to) return null;
                  const source = nodesById.get(edge.source)!;
                  const target = nodesById.get(edge.target)!;
                  const relationLabel = t(edge.ontology_label ?? edge.edge_type_code);
                  const relationLines = wrapLabel(relationLabel, KNOWLEDGE_LABEL_CHARS);
                  const midX = (from.x + to.x) / 2;
                  const midY = (from.y + to.y) / 2 - 6;
                  return (
                    <g key={`${edge.source}-${edge.target}-${index}`} className="knowledge-graph-edge">
                      <path d={edgePath(from, to)} markerEnd={`url(#${markerId})`} />
                      <text
                        className="knowledge-graph-edge-label"
                        x={midX}
                        y={midY}
                        textAnchor="middle"
                      >
                        {wrapTspans(relationLines, midX, 12)}
                      </text>
                      <title>
                        {`${source.label} → ${target.label} · ${relationLabel}`}
                        {edge.evidence_text ? ` · ${edge.evidence_text}` : ""}
                      </title>
                    </g>
                  );
                })}
                {graph.nodes.map((node) => {
                  const position = positions.get(node.id)!;
                  const isPost = node.node_type_code === "node_post";
                  const nodeClass = node.is_focus ? "focus" : node.is_evidence_text_node ? "evidence" : "catalog";
                  const label = nodeCaption(node);
                  return (
                    <g
                      key={node.id}
                      className={`knowledge-graph-node ${nodeClass}${isPost && onSelectPost ? " interactive" : ""}`}
                      transform={`translate(${position.x}, ${position.y})`}
                      role={isPost && onSelectPost ? "button" : undefined}
                      tabIndex={isPost && onSelectPost ? 0 : undefined}
                      onClick={
                        isPost && onSelectPost
                          ? () => {
                              if (Date.now() - lastPanAtRef.current < 250) return;
                              onSelectPost(node.node_id);
                            }
                          : undefined
                      }
                      onKeyDown={
                        isPost && onSelectPost
                          ? (event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                onSelectPost(node.node_id);
                              }
                            }
                          : undefined
                      }
                      aria-label={isPost && onSelectPost ? tf("Open post: {label}", { label }) : label}
                    >
                      <rect
                        x={-position.width / 2}
                        y={-position.height / 2}
                        width={position.width}
                        height={position.height}
                        rx="10"
                      />
                      <text
                        className="knowledge-graph-node-label"
                        textAnchor="middle"
                        y={-position.height / 2 + 16}
                      >
                        {wrapTspans(position.lines, 0, LINE_H)}
                      </text>
                      <text
                        className="knowledge-graph-node-type"
                        textAnchor="middle"
                        y={-position.height / 2 + 16 + position.lines.length * LINE_H + 2}
                      >
                        {wrapTspans(position.typeLines, 0, 12)}
                      </text>
                      <title>{label}</title>
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>
          {graph.edges.length > 0 ? (
            <details className="knowledge-graph-evidence" open>
              <summary>{t("Evidence trail")}</summary>
              <div className="knowledge-graph-table-wrap">
                <table aria-label={`${t("Knowledge Graph")} — ${t("Evidence trail")}`}>
                  <thead>
                    <tr>
                      <th scope="col">{t("Source")}</th>
                      <th scope="col">{t("Relation")}</th>
                      <th scope="col">{t("Target")}</th>
                      <th scope="col">{t("Evidence")}</th>
                      <th scope="col">{t("Confidence")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {graph.edges.map((edge, index) => {
                      const source = nodesById.get(edge.source);
                      const target = nodesById.get(edge.target);
                      return (
                        <tr key={`${edge.edge_type_code}-${index}`}>
                          <td>{source?.label ?? edge.source}</td>
                          <td>{t(edge.ontology_label ?? edge.edge_type_code)}</td>
                          <td>{target?.label ?? edge.target}</td>
                          <td>{edge.evidence_text ?? "—"}</td>
                          <td>{Math.round(edge.confidence * 100)}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </details>
          ) : null}
        </>
      )}
    </section>
  );
}
