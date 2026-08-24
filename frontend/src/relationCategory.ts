/**
 * Classifies a Knowledge Graph `edge_type_code` into the coarse relation
 * category the graph's legend and evidence table explain to a general
 * audience: precedence in time, hierarchy (broader/narrower, member-of),
 * cause and effect, or everything else.
 *
 * Codes are drawn from `docs/ontology/lineageweave-kg.ttl`'s
 * `semanticPredicateRegistry` (the `predicateCode` values extracted
 * relations use) plus the catalog `edge_type_code` constants in
 * `lineageweave/knowledge_graph.py`.
 */

export type RelationCategory = "temporal" | "hierarchical" | "causal" | "other";

const HIERARCHICAL_RELATIONS = new Set([
  "skos_broader",
  "org_suborganization_of",
  "org_unit_of",
  "org_member_of",
  "org_has_membership",
  "prov_specialization_of",
  "edge_affiliation",
  "edge_team_affiliation",
]);

const CAUSAL_RELATIONS = new Set([
  "lw_has_cause",
  "lw_has_consequence",
  "lw_has_next_step",
  "lw_has_goal",
  "lw_has_result",
  "prov_was_influenced_by",
]);

export function relationCategory(edgeTypeCode: string): RelationCategory {
  if (edgeTypeCode.startsWith("time_") || edgeTypeCode === "sosa_phenomenon_time" || edgeTypeCode === "lw_has_time") {
    return "temporal";
  }
  if (HIERARCHICAL_RELATIONS.has(edgeTypeCode)) return "hierarchical";
  if (CAUSAL_RELATIONS.has(edgeTypeCode)) return "causal";
  return "other";
}

/**
 * Layout-only precedence: which endpoint should render closer to the top
 * for a given predicate. This never changes the drawn arrow (still always
 * source -> target, the true stored direction) -- it only orders rows so
 * "earlier"/"broader"/"cause" nodes land above "later"/"narrower"/"effect"
 * nodes instead of an arbitrary array position. Predicates absent here have
 * no established layout precedence and keep their original relative order.
 */
const ORDER_DIRECTION: Record<string, "forward" | "reverse"> = {
  time_before: "forward",
  time_after: "reverse",
  skos_broader: "reverse",
  org_suborganization_of: "reverse",
  org_unit_of: "reverse",
  org_member_of: "reverse",
  edge_affiliation: "reverse",
  edge_team_affiliation: "reverse",
  lw_has_cause: "reverse",
  lw_has_consequence: "forward",
  lw_has_next_step: "forward",
};

export function precedenceFromEdges(
  edges: readonly { source: string; target: string; edge_type_code: string }[],
): Map<string, string[]> {
  const precedes = new Map<string, string[]>();
  for (const edge of edges) {
    const direction = ORDER_DIRECTION[edge.edge_type_code];
    if (!direction) continue;
    const before = direction === "forward" ? edge.source : edge.target;
    const after = direction === "forward" ? edge.target : edge.source;
    if (before === after) continue;
    const existing = precedes.get(before);
    if (existing) existing.push(after);
    else precedes.set(before, [after]);
  }
  return precedes;
}

/**
 * Stable Kahn's-algorithm topological sort. Nodes with no established
 * precedence keep their original relative order; a cycle among the
 * remaining nodes (contradictory predicates) falls back to draining them
 * in original order rather than guessing a direction that isn't supported.
 */
export function topologicalOrder(ids: string[], precedes: Map<string, string[]>): string[] {
  const indegree = new Map(ids.map((id) => [id, 0]));
  precedes.forEach((afters) => {
    afters.forEach((after) => {
      if (indegree.has(after)) indegree.set(after, (indegree.get(after) ?? 0) + 1);
    });
  });
  const remaining = new Set(ids);
  const order: string[] = [];
  while (remaining.size > 0) {
    const ready = ids.filter((id) => remaining.has(id) && indegree.get(id) === 0);
    const batch = ready.length > 0 ? ready : ids.filter((id) => remaining.has(id));
    batch.forEach((id) => {
      order.push(id);
      remaining.delete(id);
      (precedes.get(id) ?? []).forEach((after) => {
        if (remaining.has(after)) indegree.set(after, (indegree.get(after) ?? 0) - 1);
      });
    });
    if (ready.length === 0) break;
  }
  return order;
}
