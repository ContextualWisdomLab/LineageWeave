import { useEffect, useMemo, useState } from "react";
import {
  BackendError,
  fetchOntologyNeighborhood,
  type OntologyGraphEdgePayload,
  type OntologyGraphNodePayload,
  type OntologyNeighborhoodPayload,
} from "../api";
import { t, tf } from "../i18n";
import { layoutOntologyNeighborhood, neighborhoodCsv } from "../ontologyLayout";

export type OntologyExplorerStatus =
  | "ready"
  | "loading"
  | "empty"
  | "truncated"
  | "denied"
  | "stale"
  | "rejected"
  | "error";

export type OntologyExplorerProps = {
  accessToken?: string;
  focusNodeType: string;
  focusNodeId: string;
  neighborhood?: OntologyNeighborhoodPayload | null;
  status?: OntologyExplorerStatus;
  knowledgeCutoff?: string;
  onSelectPost?: (postId: string) => void;
  onOpenEvidence?: (postId: string) => void;
};

const NODE_TYPE_LABEL: Record<string, string> = {
  node_post: "Post",
  node_person: "Person",
  node_corporate_entity: "Organization",
  node_team: "Team",
};

const TRUTH_LABEL: Record<string, string> = {
  truth_authoritative: "Authoritative",
  truth_observed: "Observed",
  truth_inferred: "Inferred",
  truth_proposed: "Proposed",
  truth_superseded: "Superseded",
  truth_rejected: "Rejected",
};

/**
 * Inspects a typed ontology neighborhood from an authorized focus node.
 *
 * Next action: select a node or edge, then open its evidence or traverse.
 */
export function OntologyExplorer({
  accessToken,
  focusNodeType,
  focusNodeId,
  neighborhood: provided,
  status: providedStatus,
  knowledgeCutoff,
  onSelectPost,
  onOpenEvidence,
}: OntologyExplorerProps) {
  const [loaded, setLoaded] = useState<OntologyNeighborhoodPayload | null>(provided ?? null);
  const [status, setStatus] = useState<OntologyExplorerStatus>(providedStatus ?? (provided ? statusFromPayload(provided) : "loading"));
  const [query, setQuery] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [focusType, setFocusType] = useState(focusNodeType);
  const [focusId, setFocusId] = useState(focusNodeId);

  useEffect(() => {
    setFocusType(focusNodeType);
    setFocusId(focusNodeId);
  }, [focusNodeType, focusNodeId]);

  useEffect(() => {
    if (provided) {
      setLoaded(provided);
      setStatus(providedStatus ?? statusFromPayload(provided));
      return;
    }
    if (!accessToken) {
      setStatus(providedStatus ?? "empty");
      return;
    }
    let cancelled = false;
    setStatus("loading");
    fetchOntologyNeighborhood(accessToken, {
      focusNodeType: focusType,
      focusNodeId: focusId,
      knowledgeCutoff,
    })
      .then((payload) => {
        if (cancelled) return;
        setLoaded(payload);
        setStatus(statusFromPayload(payload, knowledgeCutoff));
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setLoaded(null);
        if (error instanceof BackendError && error.status === 403) {
          setStatus("denied");
          return;
        }
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken, focusType, focusId, knowledgeCutoff, provided, providedStatus]);

  const visible = useMemo(() => filterNeighborhood(loaded, query), [loaded, query]);
  const layout = useMemo(() => (visible ? layoutOntologyNeighborhood(visible) : null), [visible]);
  const selectedNode = visible?.nodes.find((node) => node.node_id === selectedNodeId) ?? null;
  const selectedEdge = visible?.edges.find((edge) => edge.edge_id === selectedEdgeId) ?? null;

  function resetFocus() {
    setFocusType(focusNodeType);
    setFocusId(focusNodeId);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setQuery("");
  }

  function exportCsv() {
    if (!visible) return;
    downloadFile("ontology-neighborhood.csv", neighborhoodCsv(visible), "text/csv");
  }

  function exportJsonld() {
    if (!visible) return;
    downloadFile(
      "ontology-neighborhood.jsonld",
      `${JSON.stringify(visible.jsonld, null, 2)}\n`,
      "application/ld+json",
    );
  }

  return (
    <section className="ontology-explorer" aria-label={t("Ontology neighborhood")}>
      <header className="ontology-explorer-header">
        <div>
          <p className="section-eyebrow">{t("Ontology neighborhood")}</p>
          <h3>{t("Typed relations, not Event Lineage")}</h3>
          <p>
            {t("This is an ontology neighborhood, not Event Lineage.")}{" "}
            {t("Event Lineage shows reconstructed post-to-post parents. This graph shows typed people, organizations, teams, and posts.")}
          </p>
        </div>
        <div className="ontology-explorer-actions">
          <button type="button" onClick={resetFocus}>
            {t("Reset focus")}
          </button>
          <button type="button" onClick={exportCsv} disabled={!visible}>
            {t("Export CSV")}
          </button>
          <button type="button" onClick={exportJsonld} disabled={!visible}>
            {t("Export JSON-LD")}
          </button>
          <button type="button" onClick={() => window.print()}>
            {t("Print this neighborhood")}
          </button>
        </div>
      </header>
      <label className="ontology-search">
        {t("Search within this neighborhood")}
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label={t("Search within this neighborhood")}
        />
      </label>
      {statusMessage(status)}
      <OntologyLegend />
      {layout && visible && status !== "denied" && status !== "error" && status !== "loading" ? (
        <>
          <div className="ontology-graph-desktop">
            <OntologyGraph
              layout={layout}
              selectedNodeId={selectedNodeId}
              selectedEdgeId={selectedEdgeId}
              onSelectNode={(node) => {
                setSelectedNodeId(node.node_id);
                setSelectedEdgeId(null);
              }}
              onSelectEdge={(edge) => {
                setSelectedEdgeId(edge.edge_id);
                setSelectedNodeId(null);
              }}
            />
          </div>
          <OntologyExactValueTable
            payload={visible}
            selectedEdgeId={selectedEdgeId}
            onSelectEdge={(edgeId) => {
              setSelectedEdgeId(edgeId);
              setSelectedNodeId(null);
            }}
          />
        </>
      ) : null}
      {selectedNode ? (
        <OntologyNodeDrawer
          node={selectedNode}
          onFocus={() => {
            setFocusType(selectedNode.node_type_code);
            setFocusId(selectedNode.node_id);
          }}
          onOpenEvidence={
            selectedNode.node_type_code === "node_post"
              ? () => (onSelectPost ?? onOpenEvidence)?.(selectedNode.node_id)
              : undefined
          }
          onClose={() => setSelectedNodeId(null)}
        />
      ) : null}
      {selectedEdge ? (
        <OntologyEdgeDrawer
          edge={selectedEdge}
          payload={visible}
          onOpenEvidence={(postId) => (onOpenEvidence ?? onSelectPost)?.(postId)}
          onClose={() => setSelectedEdgeId(null)}
        />
      ) : null}
    </section>
  );
}

function statusFromPayload(
  payload: OntologyNeighborhoodPayload,
  knowledgeCutoff?: string,
): OntologyExplorerStatus {
  if (payload.limitation_code === "neighborhood_empty") return "empty";
  if (payload.truncated || payload.limitation_code === "neighborhood_truncated") return "truncated";
  if (payload.edges.some((edge) => edge.truth_status_code === "truth_rejected")) return "rejected";
  if (knowledgeCutoff) return "stale";
  return "ready";
}

function statusMessage(status: OntologyExplorerStatus) {
  const messages: Record<OntologyExplorerStatus, string> = {
    ready: "",
    loading: t("Loading ontology neighborhood..."),
    empty: t("No visible ontology relations for this focus. Open a Keyman or affiliated organization next."),
    truncated: t("Neighborhood truncated. Page visible relations, then inspect one edge."),
    denied: t("Access denied for this ontology neighborhood. Open a visible post next."),
    stale: t("This neighborhood is bound to a knowledge cutoff. Compare with live evidence next."),
    rejected: t("Rejected proposal. Open the evidence and do not treat it as authoritative."),
    error: t("Ontology neighborhood is unavailable. Open a visible post next."),
  };
  const text = messages[status];
  if (!text) return null;
  return (
    <p className={`ontology-status ontology-status-${status}`} role="status">
      {text}
    </p>
  );
}

function OntologyLegend() {
  return (
    <details className="ontology-legend">
      <summary>{t("Legend")}</summary>
      <p>{t("Node types use shape plus text, never color alone. Truth status is labeled on every edge.")}</p>
      <ul>
        <li>{t("Post")} — {t("rectangle")}</li>
        <li>{t("Person")} — {t("ellipse")}</li>
        <li>{t("Organization")} — {t("hexagon")}</li>
        <li>{t("Team")} — {t("rounded rectangle")}</li>
      </ul>
      <ul>
        <li>{t("Authoritative")}</li>
        <li>{t("Observed")}</li>
        <li>{t("Inferred")}</li>
        <li>{t("Proposed")}</li>
        <li>{t("Superseded")}</li>
        <li>{t("Rejected")}</li>
      </ul>
      <p>{t("Hidden evidence was removed. No omitted count is shown.")}</p>
    </details>
  );
}

function OntologyGraph({
  layout,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
}: {
  layout: ReturnType<typeof layoutOntologyNeighborhood>;
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  onSelectNode: (node: OntologyGraphNodePayload) => void;
  onSelectEdge: (edge: OntologyGraphEdgePayload) => void;
}) {
  return (
    <svg
      className="ontology-graph"
      viewBox={`0 0 ${layout.width} ${layout.height}`}
      width="100%"
      height={Math.max(180, layout.height)}
    >
      <title>{t("Ontology neighborhood")}</title>
      {layout.edges.map((edge) => {
        const midX = (edge.fromX + edge.toX) / 2;
        const midY = (edge.fromY + edge.toY) / 2;
        const selected = edge.edge_id === selectedEdgeId;
        return (
          <g key={edge.edge_id}>
            <path
              className={selected ? "ontology-edge ontology-edge-selected" : "ontology-edge"}
              d={`M ${edge.fromX} ${edge.fromY} C ${midX} ${edge.fromY}, ${midX} ${edge.toY}, ${edge.toX} ${edge.toY}`}
            />
            <text
              className="ontology-edge-label"
              x={midX}
              y={midY - 6}
              textAnchor="middle"
            >
              {edge.property_label} · {t(TRUTH_LABEL[edge.truth_status_code] ?? edge.truth_status_code)}
            </text>
            <circle
              className="ontology-edge-hit"
              cx={midX}
              cy={midY}
              r={14}
              role="button"
              tabIndex={0}
              aria-label={tf("Select edge: {property} from {source} to {target}", {
                property: edge.property_label,
                source: edge.source_node_id,
                target: edge.target_node_id,
              })}
              aria-pressed={selected ? "true" : "false"}
              onClick={() => onSelectEdge(edge)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectEdge(edge);
                }
              }}
            />
          </g>
        );
      })}
      {layout.nodes.map((node) => (
        <g
          key={node.node_id}
          className={node.node_id === selectedNodeId ? "ontology-node ontology-node-selected" : "ontology-node"}
          transform={`translate(${node.x}, ${node.y})`}
          role="button"
          tabIndex={0}
          aria-label={tf("Select node: {label}", { label: `${t(NODE_TYPE_LABEL[node.node_type_code] ?? node.node_type_code)} ${node.display_label}` })}
          aria-pressed={node.node_id === selectedNodeId ? "true" : "false"}
          onClick={() => onSelectNode(node)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              onSelectNode(node);
            }
          }}
        >
          <OntologyShape shape={node.shape_code} />
          <text x={28} y={4}>
            {node.display_label}
          </text>
          <text className="ontology-node-type" x={28} y={18}>
            {t(NODE_TYPE_LABEL[node.node_type_code] ?? node.node_type_code)}
          </text>
        </g>
      ))}
    </svg>
  );
}

function OntologyShape({ shape }: { shape: string }) {
  if (shape === "ellipse") {
    return <ellipse rx={16} ry={12} />;
  }
  if (shape === "hexagon") {
    return <polygon points="-16,0 -8,-14 8,-14 16,0 8,14 -8,14" />;
  }
  if (shape === "rounded-rectangle") {
    return <rect x={-18} y={-12} width={36} height={24} rx={8} />;
  }
  return <rect x={-18} y={-12} width={36} height={24} />;
}

function OntologyExactValueTable({
  payload,
  selectedEdgeId,
  onSelectEdge,
}: {
  payload: OntologyNeighborhoodPayload;
  selectedEdgeId: string | null;
  onSelectEdge: (edgeId: string) => void;
}) {
  return (
    <div className="ontology-exact-values">
      <h4>{t("Exact values")}</h4>
      {payload.exact_value_rows.length === 0 ? (
        <p>{t("No visible ontology relations for this focus. Open a Keyman or affiliated organization next.")}</p>
      ) : (
        <table>
          <caption>{t("Exact values")}</caption>
          <thead>
            <tr>
              <th>{t("Source")}</th>
              <th>{t("Property")}</th>
              <th>{t("Target")}</th>
              <th>{t("Truth status")}</th>
              <th>{t("Recorded at")}</th>
            </tr>
          </thead>
          <tbody>
            {payload.exact_value_rows.map((row) => (
              <tr key={row.edge_id} className={row.edge_id === selectedEdgeId ? "is-selected" : undefined}>
                <td>
                  <button type="button" onClick={() => onSelectEdge(row.edge_id)}>
                    {row.source_label}
                  </button>
                </td>
                <td>{row.property_label}</td>
                <td>{row.target_label}</td>
                <td>{t(TRUTH_LABEL[row.truth_status_code] ?? row.truth_status_code)}</td>
                <td>{row.recorded_at.slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function OntologyNodeDrawer({
  node,
  onFocus,
  onOpenEvidence,
  onClose,
}: {
  node: OntologyGraphNodePayload;
  onFocus: () => void;
  onOpenEvidence?: () => void;
  onClose: () => void;
}) {
  return (
    <aside className="ontology-drawer" aria-label={t("Node evidence")}>
      <h4>{node.display_label}</h4>
      <p>
        {t(NODE_TYPE_LABEL[node.node_type_code] ?? node.node_type_code)} · {t(TRUTH_LABEL[node.truth_status_code] ?? node.truth_status_code)}
      </p>
      <p>{t("Ontology class")}: {node.ontology_class_iri}</p>
      <p>{t("Recorded at")}: {node.recorded_at.slice(0, 10)}</p>
      <div className="ontology-explorer-actions">
        <button type="button" onClick={onFocus}>
          {t("Focus this node next")}
        </button>
        {onOpenEvidence ? (
          <button type="button" onClick={onOpenEvidence}>
            {t("Open evidence post")}
          </button>
        ) : null}
        <button type="button" onClick={onClose}>
          {t("Close ontology details")}
        </button>
      </div>
    </aside>
  );
}

function OntologyEdgeDrawer({
  edge,
  payload,
  onOpenEvidence,
  onClose,
}: {
  edge: OntologyGraphEdgePayload;
  payload: OntologyNeighborhoodPayload | null;
  onOpenEvidence?: (postId: string) => void;
  onClose: () => void;
}) {
  const source = payload?.nodes.find((node) => node.node_id === edge.source_node_id);
  const target = payload?.nodes.find((node) => node.node_id === edge.target_node_id);
  return (
    <aside className="ontology-drawer" aria-label={t("Edge provenance")}>
      <h4>{edge.property_label}</h4>
      <p>
        {source?.display_label} → {target?.display_label}
      </p>
      <p>{t("Truth status")}: {t(TRUTH_LABEL[edge.truth_status_code] ?? edge.truth_status_code)}</p>
      <p>{t("Property IRI")}: {edge.ontology_property_iri}</p>
      <p>{t("Provenance")}: {edge.provenance_reference ?? t("Unknown")}</p>
      <p>{t("Valid from")}: {edge.valid_from?.slice(0, 10) || t("Unknown")}</p>
      <p>{t("Valid to")}: {edge.valid_to?.slice(0, 10) || t("Unknown")}</p>
      <p>{t("Recorded at")}: {edge.recorded_at.slice(0, 10)}</p>
      {edge.evidence_references.length > 0 ? (
        <ul>
          {edge.evidence_references.map((reference) => (
            <li key={reference}>
              {onOpenEvidence ? (
                <button type="button" onClick={() => onOpenEvidence(reference)}>
                  {tf("Open evidence: {title}", { title: reference })}
                </button>
              ) : (
                reference
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p>{t("Hidden evidence was removed. No omitted count is shown.")}</p>
      )}
      <button type="button" onClick={onClose}>
        {t("Close ontology details")}
      </button>
    </aside>
  );
}

function filterNeighborhood(
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
  const nodesById = new Map(payload.nodes.map((node) => [node.node_id, node]));
  const edges = payload.edges.filter((edge) => {
    const source = nodesById.get(edge.source_node_id);
    const target = nodesById.get(edge.target_node_id);
    return edgeMatch(edge) || Boolean(source && nodeMatch(source)) || Boolean(target && nodeMatch(target));
  });
  const keep = new Set<string>([payload.focus_node_id]);
  for (const edge of edges) {
    keep.add(edge.source_node_id);
    keep.add(edge.target_node_id);
  }
  for (const node of payload.nodes) {
    if (nodeMatch(node)) keep.add(node.node_id);
  }
  const nodes = payload.nodes.filter((node) => keep.has(node.node_id));
  const exact_value_rows = payload.exact_value_rows.filter((row) =>
    edges.some((edge) => edge.edge_id === row.edge_id),
  );
  return { ...payload, nodes, edges, exact_value_rows };
}

function downloadFile(name: string, body: string, type: string) {
  const blob = new Blob([body], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
