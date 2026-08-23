import { describe, expect, it } from "vitest";
import { precedenceFromEdges, relationCategory, topologicalOrder } from "./relationCategory";

describe("relationCategory", () => {
  it("classifies temporal predicates by the time_ prefix and the two named exceptions", () => {
    expect(relationCategory("time_before")).toBe("temporal");
    expect(relationCategory("time_after")).toBe("temporal");
    expect(relationCategory("time_interval_during")).toBe("temporal");
    expect(relationCategory("sosa_phenomenon_time")).toBe("temporal");
    expect(relationCategory("lw_has_time")).toBe("temporal");
  });

  it("classifies hierarchy predicates", () => {
    expect(relationCategory("skos_broader")).toBe("hierarchical");
    expect(relationCategory("org_suborganization_of")).toBe("hierarchical");
    expect(relationCategory("org_unit_of")).toBe("hierarchical");
    expect(relationCategory("org_member_of")).toBe("hierarchical");
    expect(relationCategory("edge_affiliation")).toBe("hierarchical");
    expect(relationCategory("edge_team_affiliation")).toBe("hierarchical");
  });

  it("classifies causal predicates", () => {
    expect(relationCategory("lw_has_cause")).toBe("causal");
    expect(relationCategory("lw_has_consequence")).toBe("causal");
    expect(relationCategory("lw_has_next_step")).toBe("causal");
  });

  it("falls back to other for unrecognized or undirected predicates", () => {
    expect(relationCategory("edge_co_mention")).toBe("other");
    expect(relationCategory("edge_mention")).toBe("other");
    expect(relationCategory("dct_references")).toBe("other");
    expect(relationCategory("")).toBe("other");
  });
});

describe("precedenceFromEdges", () => {
  it("orders a reverse predicate's after-node ahead of its source", () => {
    const precedes = precedenceFromEdges([
      { source: "child", target: "parent", edge_type_code: "org_suborganization_of" },
    ]);
    expect(precedes.get("parent")).toEqual(["child"]);
  });

  it("orders a forward predicate's source ahead of its target", () => {
    const precedes = precedenceFromEdges([{ source: "earlier", target: "later", edge_type_code: "time_before" }]);
    expect(precedes.get("earlier")).toEqual(["later"]);
  });

  it("accumulates multiple afters for the same before-node", () => {
    const precedes = precedenceFromEdges([
      { source: "earlier", target: "middle", edge_type_code: "time_before" },
      { source: "earlier", target: "late", edge_type_code: "time_before" },
    ]);
    expect(precedes.get("earlier")).toEqual(["middle", "late"]);
  });

  it("ignores predicates with no established layout direction", () => {
    const precedes = precedenceFromEdges([{ source: "a", target: "b", edge_type_code: "edge_co_mention" }]);
    expect(precedes.size).toBe(0);
  });

  it("drops self-referential edges rather than creating a same-node cycle", () => {
    const precedes = precedenceFromEdges([{ source: "a", target: "a", edge_type_code: "time_before" }]);
    expect(precedes.size).toBe(0);
  });
});

describe("topologicalOrder", () => {
  it("keeps original order when no precedence is established", () => {
    expect(topologicalOrder(["x", "y", "z"], new Map())).toEqual(["x", "y", "z"]);
  });

  it("reorders a chain declared out of order", () => {
    const precedes = new Map([
      ["a", ["b"]],
      ["b", ["c"]],
    ]);
    expect(topologicalOrder(["c", "a", "b"], precedes)).toEqual(["a", "b", "c"]);
  });

  it("drains a cycle in original order instead of guessing a direction", () => {
    const precedes = new Map([
      ["a", ["b"]],
      ["b", ["a"]],
    ]);
    expect(topologicalOrder(["a", "b"], precedes)).toEqual(["a", "b"]);
  });
});
