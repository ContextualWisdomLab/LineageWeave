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

export const ONTOLOGY_NODE_LABEL_WIDTH = 184;

const COLUMN_GAP = 260;
const ROW_GAP = 88;
const LEFT = ONTOLOGY_NODE_LABEL_WIDTH / 2 + 20;
const TOP = 48;

function nodeKey(nodeTypeCode: string, nodeId: string): string {
  return `${nodeTypeCode}:${nodeId}`;
}

/**
 * Deterministic left-to-right neighborhood layout from the focus node.
 *
 * Next action: render the coordinates, then select a node or edge to
 * inspect its authorized evidence.
 */
export function layoutOntologyNeighborhood(payload: OntologyNeighborhoodPayload): OntologyLayout {
  const byKey = new Map(payload.nodes.map((node) => [nodeKey(node.node_type_code, node.node_id), node]));
  const adjacency = new Map<string, string[]>();
  for (const node of payload.nodes) {
    adjacency.set(nodeKey(node.node_type_code, node.node_id), []);
  }
  for (const edge of payload.edges) {
    const sourceKey = nodeKey(edge.source_node_type_code, edge.source_node_id);
    const targetKey = nodeKey(edge.target_node_type_code, edge.target_node_id);
    if (!byKey.has(sourceKey) || !byKey.has(targetKey)) {
      continue;
    }
    adjacency.get(sourceKey)?.push(targetKey);
    adjacency.get(targetKey)?.push(sourceKey);
  }
  for (const [nodeId, neighbors] of adjacency) {
    adjacency.set(nodeId, [...new Set(neighbors)].sort());
  }

  const depth = new Map<string, number>();
  const focusKey = nodeKey(payload.focus_node_type_code, payload.focus_node_id);
  const queue = [focusKey];
  depth.set(focusKey, 0);
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
    const column = depth.get(nodeKey(node.node_type_code, node.node_id)) ?? 0;
    const bucket = columns.get(column) ?? [];
    bucket.push(nodeKey(node.node_type_code, node.node_id));
    columns.set(column, bucket);
  }
  for (const [column, ids] of columns) {
    columns.set(
      column,
      [...ids].sort((left, right) => {
        const leftLabel = byKey.get(left)?.display_label ?? left;
        const rightLabel = byKey.get(right)?.display_label ?? right;
        return compareCodeUnits(leftLabel, rightLabel) || compareCodeUnits(left, right);
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
      const node = byKey.get(nodeId);
      if (!node) return;
      positioned.set(nodeId, {
        ...node,
        depth: column,
        x: LEFT + column * COLUMN_GAP,
        y: TOP + index * ROW_GAP,
      });
    });
  }

  const nodes = payload.nodes
    .map((node) => positioned.get(nodeKey(node.node_type_code, node.node_id)))
    .filter((node): node is LaidOutOntologyNode => Boolean(node));
  const edges: LaidOutOntologyEdge[] = payload.edges.flatMap((edge) => {
    const from = positioned.get(nodeKey(edge.source_node_type_code, edge.source_node_id));
    const to = positioned.get(nodeKey(edge.target_node_type_code, edge.target_node_id));
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

function compareCodeUnits(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

/**
 * Restrict every exportable projection to the graph visible after search.
 *
 * Next action: export CSV or JSON-LD to carry the same authorized subset.
 */
export function filterNeighborhood(
  payload: OntologyNeighborhoodPayload | null,
  query: string,
): OntologyNeighborhoodPayload | null {
  if (!payload) return null;
  const needle = query.trim().toLowerCase();
  if (!needle) return payload;
  const nodeMatch = (node: OntologyGraphNodePayload) =>
    `${node.display_label} ${node.node_type_code} ${node.truth_status_code}`.toLowerCase().includes(needle);
  const edgeMatch = (edge: OntologyGraphEdgePayload) =>
    `${edge.property_label} ${edge.property_code} ${edge.truth_status_code}`.toLowerCase().includes(needle);
  const nodesByKey = new Map(payload.nodes.map((node) => [nodeKey(node.node_type_code, node.node_id), node]));
  const edges = payload.edges.filter((edge) => {
    const source = nodesByKey.get(nodeKey(edge.source_node_type_code, edge.source_node_id));
    const target = nodesByKey.get(nodeKey(edge.target_node_type_code, edge.target_node_id));
    return edgeMatch(edge) || Boolean(source && nodeMatch(source)) || Boolean(target && nodeMatch(target));
  });
  const keep = new Set<string>([nodeKey(payload.focus_node_type_code, payload.focus_node_id)]);
  for (const edge of edges) {
    keep.add(nodeKey(edge.source_node_type_code, edge.source_node_id));
    keep.add(nodeKey(edge.target_node_type_code, edge.target_node_id));
  }
  for (const node of payload.nodes) {
    if (nodeMatch(node)) keep.add(nodeKey(node.node_type_code, node.node_id));
  }
  const nodes = payload.nodes.filter((node) => keep.has(nodeKey(node.node_type_code, node.node_id)));
  const exact_value_rows = payload.exact_value_rows.filter((row) =>
    edges.some((edge) => edge.edge_id === row.edge_id) ||
    (payload.voice_assignments ?? []).some(
      (assignment) =>
        row.edge_id === `voice-assignment:${assignment.post_id}:${assignment.voice_type_code}` &&
        keep.has(nodeKey("node_post", assignment.post_id)),
    ),
  );
  const visibleIds = new Set([
    ...nodes.map((node) => `lw:node/${node.node_type_code}/${node.node_id}`),
    ...edges.map((edge) => `lw:edge/${edge.edge_id}`),
  ]);
  const visibleNodeSuffixes = nodes.map(
    (node) => `node/${encodeURIComponent(node.node_type_code)}/${node.node_id}`,
  );
  const visibleVoiceAssignments = (payload.voice_assignments ?? []).filter((assignment) =>
    keep.has(nodeKey("node_post", assignment.post_id)),
  );
  const visibleVoiceIds = new Set(
    visibleVoiceAssignments.flatMap((assignment) => [
      assignment.voice_type_iri,
      `voice-assignment/${assignment.post_id}/${assignment.voice_type_code}`,
    ]),
  );
  const visibleVoiceIdSuffixes = [...visibleVoiceIds];
  const graph = payload.jsonld["@graph"];
  const jsonld = Array.isArray(graph)
    ? {
        ...payload.jsonld,
        "@graph": graph.filter(
          (item): item is Record<string, unknown> =>
            typeof item === "object" && item !== null &&
            typeof item["@id"] === "string" &&
            (visibleIds.has(item["@id"]) ||
              visibleNodeSuffixes.some((suffix) => item["@id"].endsWith(suffix)) ||
              visibleVoiceIds.has(item["@id"]) ||
              visibleVoiceIdSuffixes.some((id) => item["@id"].endsWith(id))),
        ),
      }
    : payload.jsonld;
  return {
    ...payload,
    nodes,
    edges,
    exact_value_rows,
    voice_assignments: visibleVoiceAssignments,
    jsonld,
  };
}

/**
 * Accumulate a later neighborhood page onto the already-visible graph.
 *
 * Next action: keep the selected evidence, then inspect or page again.
 */
export function accumulateNeighborhoodPages(
  current: OntologyNeighborhoodPayload,
  next: OntologyNeighborhoodPayload,
): OntologyNeighborhoodPayload {
  const nodes = new Map(current.nodes.map((node) => [nodeKey(node.node_type_code, node.node_id), node]));
  for (const node of next.nodes) {
    nodes.set(nodeKey(node.node_type_code, node.node_id), node);
  }
  const edges = new Map(current.edges.map((edge) => [edge.edge_id, edge]));
  for (const edge of next.edges) {
    edges.set(edge.edge_id, edge);
  }
  const rows = new Map(current.exact_value_rows.map((row) => [row.edge_id, row]));
  for (const row of next.exact_value_rows) {
    rows.set(row.edge_id, row);
  }
  const voiceAssignments = new Map(
    (current.voice_assignments ?? []).map((assignment) => [
      `${assignment.post_id}:${assignment.voice_type_code}`,
      assignment,
    ]),
  );
  for (const assignment of next.voice_assignments ?? []) {
    voiceAssignments.set(`${assignment.post_id}:${assignment.voice_type_code}`, assignment);
  }
  const graphItems = new Map<string, Record<string, unknown>>();
  for (const payload of [current, next]) {
    const graph = payload.jsonld["@graph"];
    if (!Array.isArray(graph)) continue;
    for (const item of graph) {
      if (typeof item === "object" && item !== null && typeof item["@id"] === "string") {
        graphItems.set(item["@id"], item as Record<string, unknown>);
      }
    }
  }
  return {
    ...next,
    nodes: [...nodes.values()],
    edges: [...edges.values()],
    exact_value_rows: [...rows.values()],
    voice_assignments: [...voiceAssignments.values()],
    jsonld: {
      ...next.jsonld,
      "@graph": [...graphItems.values()],
    },
  };
}
