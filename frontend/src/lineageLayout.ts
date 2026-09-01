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

function isUngroupedGroup(group: string): boolean {
  return !group || UUID_GROUP.test(group);
}

export function groupHeading(group: string): string {
  if (isUngroupedGroup(group)) return "Ungrouped";
  return group;
}

function stableTextCompare(left: string, right: string): number {
  return Number(left > right) - Number(left < right);
}

/**
 * Stable presentation key for a lineage node.
 *
 * Event time is the meaningful primary order for a lineage. The opaque node
 * id is only the deterministic tie-breaker, so backend array order can never
 * move a node to a different row or keyboard position.
 */
function stableNodeSortKey(node: LineageGraphNode): string {
  return `${node.occurred_at ?? ""}\u0000${node.id}`;
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
  const orderedNodes = [...nodes].sort((left, right) =>
    stableTextCompare(stableNodeSortKey(left), stableNodeSortKey(right)),
  );
  const byId = new Map(orderedNodes.map((node) => [node.id, node]));
  const children = childrenByParent(edges);
  const hasParent = new Set(edges.map((edge) => edge.target));
  const roots = orderedNodes.filter((node) => !hasParent.has(node.id));
  const positions = new Map<string, { x: number; y: number }>();
  const visiting = new Set<string>();
  let nextRow = 0;

  const walk = (id: string, depth: number) => {
    if (positions.has(id)) return;
    visiting.add(id);
    const kids = (children.get(id) ?? [])
      .filter(
        (childId) => byId.has(childId) && !positions.has(childId) && !visiting.has(childId),
      )
      .sort((leftId, rightId) =>
        stableTextCompare(
          stableNodeSortKey(byId.get(leftId)!),
          stableNodeSortKey(byId.get(rightId)!),
        ),
      );
    if (kids.length === 0) {
      positions.set(id, { x: PAD + depth * COL_W, y: PAD + nextRow * ROW_H });
      nextRow += 1;
      visiting.delete(id);
      return;
    }
    const startRow = nextRow;
    for (const childId of kids) walk(childId, depth + 1);
    const midRow = (startRow + nextRow - 1) / 2;
    positions.set(id, { x: PAD + depth * COL_W, y: PAD + midRow * ROW_H });
    visiting.delete(id);
  };

  for (const root of roots) walk(root.id, 0);
  for (const node of orderedNodes) {
    if (!positions.has(node.id)) {
      positions.set(node.id, { x: PAD, y: PAD + nextRow * ROW_H });
      nextRow += 1;
    }
  }

  const positioned = orderedNodes.map((node) => {
    const pos = positions.get(node.id)!;
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
    truncated: graph.truncated,
    reconstruction: graph.reconstruction,
  };
}

/** Return a locale-independent key without collapsing raw reconstruct-group identity. */
function stableGroupSortKey(group: LaidOutGroup): string {
  const ungroupedRank = isUngroupedGroup(group.group) ? "1" : "0";
  return `${ungroupedRank}\u0000${group.heading}\u0000${group.group}`;
}

function stableChannelEvidenceKey(edge: LineageGraphEdge): string {
  const evidence = (edge.channel_evidence ?? [])
    .map((item) => [
      item.signal_code,
      item.signal_label,
      item.score,
      item.weight,
      item.contribution,
      item.rank,
    ])
    .sort((left, right) => stableTextCompare(JSON.stringify(left), JSON.stringify(right)));
  return JSON.stringify(evidence);
}

/**
 * Stable edge key that also distinguishes parallel relationships.
 *
 * Source and target identity alone is insufficient because the API permits more than one
 * relationship between the same posts. Relation, score, and evidence fields complete the
 * presentation tie-breaker without mutating the edge or assigning synthetic identity.
 */
function stableEdgeSortKey(
  edge: LineageGraphEdge,
  nodesById: Map<string, LineageGraphNode>,
): string {
  const source = nodesById.get(edge.source);
  const target = nodesById.get(edge.target);
  return JSON.stringify([
    source ? stableNodeSortKey(source) : edge.source,
    target ? stableNodeSortKey(target) : edge.target,
    edge.source,
    edge.target,
    edge.interval_relation_code ?? "",
    edge.interval_relation_label ?? "",
    edge.fused_score,
    stableChannelEvidenceKey(edge),
  ]);
}

/** Lay out only relationships whose two endpoints share one visible group. */
export function layoutLineageDag(graph: LineageGraph): LaidOutGroup[] {
  const buckets = new Map<string, { nodes: LineageGraphNode[]; edges: LineageGraphEdge[] }>();
  const nodesById = new Map(graph.nodes.map((node) => [node.id, node]));
  for (const node of graph.nodes) {
    const group = node.group || "";
    const bucket = buckets.get(group) ?? { nodes: [], edges: [] };
    bucket.nodes.push(node);
    buckets.set(group, bucket);
  }
  for (const edge of graph.edges) {
    const source = nodesById.get(edge.source);
    const target = nodesById.get(edge.target);
    if (!source || !target) continue;
    const sourceGroup = source.group || "";
    const targetGroup = target.group || "";
    if (sourceGroup !== targetGroup) continue;
    buckets.get(sourceGroup)!.edges.push(edge);
  }

  const groups = [...buckets.entries()].map(([group, { nodes, edges }]) => {
    const orderedEdges = [...edges].sort((left, right) =>
      stableTextCompare(
        stableEdgeSortKey(left, nodesById),
        stableEdgeSortKey(right, nodesById),
      ),
    );
    const laid = layoutGroup(nodes, orderedEdges);
    return {
      group,
      heading: groupHeading(group),
      nodes: laid.positioned,
      edges: orderedEdges,
      width: laid.width,
      height: laid.height,
    };
  });

  groups.sort((a, b) =>
    stableTextCompare(stableGroupSortKey(a), stableGroupSortKey(b)),
  );
  return groups;
}
