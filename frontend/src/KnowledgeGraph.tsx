import { useId, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import type { KnowledgeGraph, KnowledgeGraphNode } from "./api";
import { t, tf } from "./i18n";
import "./KnowledgeGraph.css";

const WIDTH = 760;
const NODE_W = 170;
const NODE_H = 42;
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

function shortLabel(value: string): string {
  return value.length > 24 ? `${value.slice(0, 23)}…` : value;
}

function nodePositions(graph: KnowledgeGraph): Map<string, { x: number; y: number }> {
  const focus = graph.nodes.find((node) => node.is_focus);
  const others = graph.nodes.filter((node) => !node.is_focus);
  const height = Math.max(260, (others.length + 1) * 68);
  const positions = new Map<string, { x: number; y: number }>();
  if (focus) positions.set(focus.id, { x: WIDTH / 2, y: height / 2 });
  others.forEach((node, index) => {
    const left = index % 2 === 0;
    const row = Math.floor(index / 2);
    positions.set(node.id, {
      x: left ? 110 : WIDTH - 110,
      y: 46 + row * 68,
    });
  });
  return positions;
}

function edgePath(from: { x: number; y: number }, to: { x: number; y: number }): string {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  const ux = dx / length;
  const uy = dy / length;
  const startX = from.x + ux * (NODE_W / 2);
  const startY = from.y + uy * (NODE_H / 2);
  const endX = to.x - ux * (NODE_W / 2);
  const endY = to.y - uy * (NODE_H / 2);
  return `M ${startX} ${startY} L ${endX} ${endY}`;
}

function nodeCaption(node: KnowledgeGraphNode): string {
  return node.is_evidence_text_node ? `${node.label} (${node.ontology_label ?? node.node_type_code})` : node.label;
}

export function KnowledgeGraphView({
  graph,
  onSelectPost,
}: {
  graph: KnowledgeGraph;
  onSelectPost?: (postId: string) => void;
}) {
  const markerId = `knowledge-graph-arrow-${useId().replaceAll(":", "")}`;
  const positions = nodePositions(graph);
  const height = Math.max(260, (graph.nodes.filter((node) => !node.is_focus).length + 1) * 68);
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
      const viewX = (localX / rect.width) * WIDTH;
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
    if (event.button !== 0 || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
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
    const dx = (event.clientX - drag.startX) * (WIDTH / drag.svgWidth);
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
          <div className="knowledge-graph-controls" aria-label={t("Graph controls")}>
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
          <div
            className="knowledge-graph-viewport"
            role="region"
            aria-label={t("Knowledge Graph")}
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
            <svg ref={svgRef} viewBox={`0 0 ${WIDTH} ${height}`} width="100%" height={height} role="img">
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
                  const source = nodesById.get(edge.source);
                  const target = nodesById.get(edge.target);
                  return (
                    <g key={`${edge.source}-${edge.target}-${index}`} className="knowledge-graph-edge">
                      <path d={edgePath(from, to)} markerEnd={`url(#${markerId})`} />
                      <title>
                        {`${source?.label ?? edge.source} → ${target?.label ?? edge.target} · ${edge.ontology_label ?? edge.edge_type_code}`}
                        {edge.evidence_text ? ` · ${edge.evidence_text}` : ""}
                      </title>
                    </g>
                  );
                })}
                {graph.nodes.map((node) => {
                  const position = positions.get(node.id);
                  if (!position) return null;
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
                      <rect x={-NODE_W / 2} y={-NODE_H / 2} width={NODE_W} height={NODE_H} rx="10" />
                      <text className="knowledge-graph-node-label" textAnchor="middle" y="-2">
                        {shortLabel(label)}
                      </text>
                      <text className="knowledge-graph-node-type" textAnchor="middle" y="14">
                        {node.ontology_label ?? node.node_type_code}
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
              <ul>
                {graph.edges.map((edge, index) => {
                  const source = nodesById.get(edge.source);
                  const target = nodesById.get(edge.target);
                  return (
                    <li key={`${edge.edge_type_code}-${index}`}>
                      <strong>{edge.ontology_label ?? edge.edge_type_code}</strong>{": "}
                      {source?.label ?? edge.source} → {target?.label ?? edge.target}
                      {edge.evidence_text ? <span> — {edge.evidence_text}</span> : null}
                    </li>
                  );
                })}
              </ul>
            </details>
          ) : null}
        </>
      )}
    </section>
  );
}
