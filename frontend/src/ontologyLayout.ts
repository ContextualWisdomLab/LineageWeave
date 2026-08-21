import type { OntologyGraphEdgePayload, OntologyGraphNodePayload, OntologyNeighborhoodPayload } from "./api";

export type LaidOutOntologyNode = OntologyGraphNodePayload & {
  x: number;
  y: number;
  depth: number;
};

export type LaidOutOntologyEdge = OntologyGraphEdgePayload & {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
};

export type OntologyLayout = {
  width: number;
  height: number;
  nodes: LaidOutOntologyNode[];
  edges: LaidOutOntologyEdge[];
};

const COLUMN_GAP = 220;
const ROW_GAP = 88;
const LEFT = 72;
const TOP = 48;

/**
 * Deterministic left-to-right neighborhood layout from the focus node.
 *
 * Next action: render the coordinates, then select a node or edge to
 * inspect its authorized evidence.
 */
export function layoutOntologyNeighborhood(payload: OntologyNeighborhoodPayload): OntologyLayout {
  const byId = new Map(payload.nodes.map((node) => [node.node_id, node]));
  const adjacency = new Map<string, string[]>();
  for (const node of payload.nodes) {
    adjacency.set(node.node_id, []);
  }
  for (const edge of payload.edges) {
    if (!byId.has(edge.source_node_id) || !byId.has(edge.target_node_id)) {
      continue;
    }
    adjacency.get(edge.source_node_id)?.push(edge.target_node_id);
    adjacency.get(edge.target_node_id)?.push(edge.source_node_id);
  }
  for (const [nodeId, neighbors] of adjacency) {
    adjacency.set(nodeId, [...new Set(neighbors)].sort());
  }

  const depth = new Map<string, number>();
  const queue = [payload.focus_node_id];
  depth.set(payload.focus_node_id, 0);
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current) break;
    const currentDepth = depth.get(current) ?? 0;
    for (const neighbor of adjacency.get(current) ?? []) {
      if (!depth.has(neighbor)) {
        depth.set(neighbor, currentDepth + 1);
        queue.push(neighbor);
      }
    }
  }

  const columns = new Map<number, string[]>();
  for (const node of payload.nodes) {
    const column = depth.get(node.node_id) ?? 0;
    const bucket = columns.get(column) ?? [];
    bucket.push(node.node_id);
    columns.set(column, bucket);
  }
  for (const [column, ids] of columns) {
    columns.set(
      column,
      [...ids].sort((left, right) => {
        const leftLabel = byId.get(left)?.display_label ?? left;
        const rightLabel = byId.get(right)?.display_label ?? right;
        return leftLabel.localeCompare(rightLabel) || left.localeCompare(right);
      }),
    );
  }

  const positioned = new Map<string, LaidOutOntologyNode>();
  let maxColumn = 0;
  let maxRow = 1;
  for (const [column, ids] of [...columns.entries()].sort((left, right) => left[0] - right[0])) {
    maxColumn = Math.max(maxColumn, column);
    maxRow = Math.max(maxRow, ids.length);
    ids.forEach((nodeId, index) => {
      const node = byId.get(nodeId);
      if (!node) return;
      positioned.set(nodeId, {
        ...node,
        depth: column,
        x: LEFT + column * COLUMN_GAP,
        y: TOP + index * ROW_GAP,
      });
    });
  }

  const nodes = payload.nodes.map((node) => positioned.get(node.node_id)).filter((node): node is LaidOutOntologyNode => Boolean(node));
  const edges: LaidOutOntologyEdge[] = payload.edges.flatMap((edge) => {
    const from = positioned.get(edge.source_node_id);
    const to = positioned.get(edge.target_node_id);
    if (!from || !to) return [];
    return [{ ...edge, fromX: from.x, fromY: from.y, toX: to.x, toY: to.y }];
  });

  return {
    width: LEFT * 2 + Math.max(maxColumn, 1) * COLUMN_GAP,
    height: TOP * 2 + Math.max(maxRow, 1) * ROW_GAP,
    nodes,
    edges,
  };
}

export function neighborhoodCsv(payload: OntologyNeighborhoodPayload): string {
  const header = [
    "edge_id",
    "source_label",
    "property_label",
    "target_label",
    "truth_status_code",
    "recorded_at",
    "ontology_property_iri",
  ];
  const lines = [header.join(",")];
  for (const row of payload.exact_value_rows) {
    lines.push(
      header
        .map((key) => csvCell(String(row[key as keyof typeof row] ?? "")))
        .join(","),
    );
  }
  return `${lines.join("\n")}\n`;
}

function csvCell(value: string): string {
  const safeValue = /^[=+\-@]/.test(value) ? `'${value}` : value;
  if (/[",\n]/.test(safeValue)) {
    return `"${safeValue.replaceAll('"', '""')}"`;
  }
  return safeValue;
}
