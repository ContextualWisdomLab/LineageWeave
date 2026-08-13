import type { LineageGraph, LineageGraphEdge, LineageGraphNode } from "./api";

export const COL_W = 220;
export const ROW_H = 52;
export const PAD = 28;

const UUID_GROUP = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface PositionedNode extends LineageGraphNode {
  x: number;
  y: number;
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
  const children = childrenByParent(edges);
  const hasParent = new Set(edges.map((edge) => edge.target));
  const roots = nodes.filter((node) => !hasParent.has(node.id));
  const positions = new Map<string, { x: number; y: number }>();
  let nextRow = 0;

  const walk = (id: string, depth: number) => {
    const kids = (children.get(id) ?? []).filter((childId) => byId.has(childId));
    if (kids.length === 0) {
      positions.set(id, { x: PAD + depth * COL_W, y: PAD + nextRow * ROW_H });
      nextRow += 1;
      return;
    }
    const startRow = nextRow;
    for (const childId of kids) walk(childId, depth + 1);
    const midRow = (startRow + nextRow - 1) / 2;
    positions.set(id, { x: PAD + depth * COL_W, y: PAD + midRow * ROW_H });
  };

  for (const root of roots) walk(root.id, 0);
  for (const node of nodes) {
    if (!positions.has(node.id)) {
      positions.set(node.id, { x: PAD, y: PAD + nextRow * ROW_H });
      nextRow += 1;
    }
  }

  const positioned = nodes.map((node) => {
    const pos = positions.get(node.id) ?? { x: PAD, y: PAD };
    return { ...node, ...pos };
  });
  const maxX = Math.max(PAD, ...positioned.map((node) => node.x));
  const maxY = Math.max(PAD, ...positioned.map((node) => node.y));
  return {
    positioned,
    width: maxX + COL_W,
    height: maxY + PAD + 16,
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
