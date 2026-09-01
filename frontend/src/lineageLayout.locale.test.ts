import { afterEach, describe, expect, it, vi } from "vitest";

import type { LineageGraph } from "./api";
import { layoutLineageDag } from "./lineageLayout";

afterEach(() => {
  vi.restoreAllMocks();
});

const groupNode = (id: string, group: string) => ({
  id,
  group,
  label: `${group} record`,
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
});
