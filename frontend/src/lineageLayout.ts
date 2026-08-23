import type { LineageGraph, LineageGraphEdge, LineageGraphNode } from "./api";
import { lineageLabelMetrics } from "./graphLabel";

/** Minimum column width; the layout grows this to fit a wrapped title. */
export const COL_W = 220;
/** Minimum row height; the layout grows this to fit wrapped title + date + kind. */
export const ROW_H = 52;
export const PAD = 28;
export const COL_GAP = 28;
export const ROW_GAP = 18;
/** Room for the on-graph Topic heading and 선·후행 axis above the first node. */
export const GROUP_HEADING_H = 44;

const UUID_GROUP = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface PositionedNode extends LineageGraphNode {
  x: number;
  y: number;
  labelLines: string[];
  labelWidth: number;
  labelHeight: number;
}

export interface LaidOutGroup {
  group: string;
  heading: string;
  nodes: PositionedNode[];
  edges: LineageGraphEdge[];
  width: number;
  height: number;
}

export function groupHeading(group: string): string {
  if (!group || UUID_GROUP.test(group)) return "Ungrouped";
  return group;
}

function childrenByParent(edges: LineageGraphEdge[]): Map<string, string[]> {
  const children = new Map<string, string[]>();
  for (const edge of edges) {
    const list = children.get(edge.source) ?? [];
    list.push(edge.target);
    children.set(edge.source, list);
  }
  return children;
}

function layoutGroup(nodes: LineageGraphNode[], edges: LineageGraphEdge[]): {
  positioned: PositionedNode[];
  width: number;
  height: number;
} {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const metrics = new Map(nodes.map((node) => [node.id, lineageLabelMetrics(node.label)]));
  const colW = Math.max(
    COL_W,
    ...[...metrics.values()].map((item) => item.labelWidth + COL_GAP),
  );
  const rowH = Math.max(
    ROW_H,
    ...[...metrics.values()].map((item) => item.labelHeight + ROW_GAP),
  );
  const children = childrenByParent(edges);
  const hasParent = new Set(edges.map((edge) => edge.target));
  const roots = nodes.filter((node) => !hasParent.has(node.id));
  const positions = new Map<string, { x: number; y: number }>();
  const visiting = new Set<string>();
  let nextRow = 0;

  const walk = (id: string, depth: number) => {
    if (positions.has(id) || visiting.has(id)) return;
    visiting.add(id);
    const kids = (children.get(id) ?? []).filter(
      (childId) => byId.has(childId) && !positions.has(childId) && !visiting.has(childId),
    );
    if (kids.length === 0) {
      positions.set(id, { x: PAD + depth * colW, y: GROUP_HEADING_H + PAD + nextRow * rowH });
      nextRow += 1;
      visiting.delete(id);
      return;
    }
    const startRow = nextRow;
    for (const childId of kids) walk(childId, depth + 1);
    const midRow = (startRow + nextRow - 1) / 2;
    positions.set(id, { x: PAD + depth * colW, y: GROUP_HEADING_H + PAD + midRow * rowH });
    visiting.delete(id);
  };

  for (const root of roots) walk(root.id, 0);
  for (const node of nodes) {
    if (!positions.has(node.id)) {
      positions.set(node.id, { x: PAD, y: GROUP_HEADING_H + PAD + nextRow * rowH });
      nextRow += 1;
    }
  }

  const positioned = nodes.map((node) => {
    const pos = positions.get(node.id) ?? { x: PAD, y: GROUP_HEADING_H + PAD };
    const box = metrics.get(node.id) ?? lineageLabelMetrics(node.label);
    return { ...node, ...pos, ...box };
  });
  const maxRight = Math.max(PAD, ...positioned.map((node) => node.x + node.labelWidth));
  const maxBottom = Math.max(PAD, ...positioned.map((node) => node.y + node.labelHeight));
  return {
    positioned,
    width: maxRight + PAD,
    height: maxBottom + PAD,
  };
}

/** Reconstruct group that contains `postId` -- the popup DAG must not mix A-100 with B-200. */
export function subgraphForPost(graph: LineageGraph, postId: string): LineageGraph {
  const focus = graph.nodes.find((node) => node.id === postId);
  if (!focus) {
    return { nodes: [], edges: [] };
  }
  const nodes = graph.nodes.filter((node) => node.group === focus.group);
  const ids = new Set(nodes.map((node) => node.id));
  return {
    nodes,
    edges: graph.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)),
  };
}

export function layoutLineageDag(graph: LineageGraph): LaidOutGroup[] {
  const buckets = new Map<string, { nodes: LineageGraphNode[]; edges: LineageGraphEdge[] }>();
  for (const node of graph.nodes) {
    const group = node.group || "Ungrouped";
    const bucket = buckets.get(group) ?? { nodes: [], edges: [] };
    bucket.nodes.push(node);
    buckets.set(group, bucket);
  }
  for (const edge of graph.edges) {
    const source = graph.nodes.find((node) => node.id === edge.source);
    const group = source?.group || "Ungrouped";
    const bucket = buckets.get(group) ?? { nodes: [], edges: [] };
    bucket.edges.push(edge);
    buckets.set(group, bucket);
  }

  const groups = [...buckets.entries()].map(([group, { nodes, edges }]) => {
    const laid = layoutGroup(nodes, edges);
    return {
      group,
      heading: groupHeading(group),
      nodes: laid.positioned,
      edges,
      width: laid.width,
      height: laid.height,
    };
  });

  groups.sort((a, b) => {
    if (a.heading === "Ungrouped" && b.heading !== "Ungrouped") return 1;
    if (b.heading === "Ungrouped" && a.heading !== "Ungrouped") return -1;
    return a.heading.localeCompare(b.heading);
  });
  return groups;
}
