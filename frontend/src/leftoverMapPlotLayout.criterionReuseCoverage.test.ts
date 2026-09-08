import { describe, expect, it } from "vitest";
import type { LeftoverMapPlottablePair } from "./leftoverMapPlotLayout";
import { layoutLeftoverMapPlot } from "./leftoverMapPlotLayout";

function pair(
  overrides: Partial<LeftoverMapPlottablePair> = {},
): LeftoverMapPlottablePair {
  return {
    pair_kind: "closest",
    post_id: "post-demo-public",
    post_title: "Public post",
    criterion_code: "sales_lead_quality",
    leftover_map_person_axis_1: 0.5,
    leftover_map_person_axis_2: 0.1,
    leftover_map_item_axis_1: 0.5,
    leftover_map_item_axis_2: -0.02,
    leftover_distance: 0.12,
    ...overrides,
  };
}

function criterionLabel(code: string): string {
  return code === "sales_lead_quality" ? "sales-lead" : "negative";
}

describe("layoutLeftoverMapPlot criterion identity", () => {
  it("reuses one item marker when distinct posts share a persisted criterion", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair(),
        pair({
          pair_kind: "farthest",
          criterion_code: "negative_sentiment",
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
        }),
        pair({
          post_id: "post-demo-spec",
          post_title: "Specification revision requested",
          leftover_map_person_axis_1: 0.9,
          leftover_map_person_axis_2: 0.8,
        }),
      ],
      criterionLabel,
    );

    expect(layout).not.toBeNull();
    expect(layout?.persons.map((marker) => marker.id)).toEqual([
      "post-demo-public",
      "post-demo-spec",
    ]);
    expect(layout?.items.map((marker) => marker.id)).toEqual([
      "sales_lead_quality",
      "negative_sentiment",
    ]);
    expect(layout?.items.filter((marker) => marker.id === "sales_lead_quality")).toHaveLength(1);
    expect(layout?.segments).toHaveLength(3);
  });
});
