import { afterEach, describe, expect, it, vi } from "vitest";

import type { LineageGraph } from "./api";
import { layoutLineageDag } from "./lineageLayout";

afterEach(() => {
  vi.restoreAllMocks();
});

const groupNode = (id: string, group: string) => ({
  id,
  group,
  label: `${group || "unassigned"} record`,
  occurred_at: "2026-01-01T00:00:00Z",
  is_root: true,
  is_branch_point: false,
});

describe("layoutLineageDag locale independence", () => {
  it("does not delegate logical reconstruct-group order to the runtime locale", () => {
    vi.spyOn(String.prototype, "localeCompare").mockImplementation(() => {
      throw new Error("runtime locale comparison must not order lineage groups");
    });

    const graph: LineageGraph = {
      nodes: [
        groupNode("zulu", "Zulu"),
        groupNode("umlaut", "Älpha"),
        groupNode("alpha", "Alpha"),
        groupNode("loose", ""),
      ],
      edges: [],
    };

    expect(layoutLineageDag(graph).map(({ heading }) => heading)).toEqual([
      "Alpha",
      "Zulu",
      "Älpha",
      "Ungrouped",
    ]);
  });

  it("keeps a named Ungrouped group distinct from truly ungrouped nodes", () => {
    const graph: LineageGraph = {
      nodes: [
        groupNode("loose", ""),
        groupNode("named-ungrouped", "Ungrouped"),
        groupNode("alpha", "Alpha"),
      ],
      edges: [],
    };

    expect(
      layoutLineageDag(graph).map(({ group, heading, nodes }) => ({
        group,
        heading,
        nodeIds: nodes.map(({ id }) => id),
      })),
    ).toEqual([
      { group: "Alpha", heading: "Alpha", nodeIds: ["alpha"] },
      {
        group: "Ungrouped",
        heading: "Ungrouped",
        nodeIds: ["named-ungrouped"],
      },
      { group: "", heading: "Ungrouped", nodeIds: ["loose"] },
    ]);
  });

  it("renders whitespace-only raw group identities with a visible Ungrouped heading", () => {
    const graph: LineageGraph = {
      nodes: [
        groupNode("spaces", "   "),
        groupNode("tab", "\t"),
      ],
      edges: [],
    };

    expect(
      layoutLineageDag(graph).map(({ group, heading, nodes }) => ({
        group,
        heading,
        nodeIds: nodes.map(({ id }) => id),
      })),
    ).toEqual([
      { group: "\t", heading: "Ungrouped", nodeIds: ["tab"] },
      { group: "   ", heading: "Ungrouped", nodeIds: ["spaces"] },
    ]);
  });
});
