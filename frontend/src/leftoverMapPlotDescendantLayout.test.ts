import { describe, expect, it } from "vitest";
import { layoutLeftoverMapPlot, type LeftoverMapPlottablePair } from "./leftoverMapPlotLayout";

function extendedPair(
  overrides: Partial<LeftoverMapPlottablePair> = {},
): LeftoverMapPlottablePair {
  return {
    pair_kind: "closest",
    post_id: "post-descendant-layout",
    post_title: "Descendant layout post",
    criterion_code: "sales_lead_quality",
    leftover_distance: 0.12,
    leftover_map_reconstruction: 0.25,
    leftover_map_explained_share: 0.76,
    leftover_map_unexplained_share: 0.24,
    leftover_map_cross_share: -0.10,
    leftover_map_unexplained: 0.50,
    leftover_residual: 0.75,
    observed_response: 2.40,
    expected_response: 2.00,
    leftover_map_rank: 0,
    leftover_map_person_axis_1: -1,
    leftover_map_person_axis_2: -1,
    leftover_map_item_axis_1: 1,
    leftover_map_item_axis_2: -1,
    ...overrides,
  };
}

describe("leftover-map descendant layout inherits #802 bounds", () => {
  it("preserves distinct persisted ticks even when their formatted labels round identically", () => {
    const layout = layoutLeftoverMapPlot(
      [
        extendedPair({
          leftover_map_person_axis_1: 0.001,
          leftover_map_item_axis_1: 0.004,
        }),
      ],
      (criterionCode) => criterionCode,
    );

    const axis1 = layout?.ticks.filter((tick) => tick.axis === 1);
    expect(axis1?.map((tick) => tick.value)).toEqual([0, 0.001, 0.004]);
    expect(axis1?.map((tick) => tick.label)).toEqual(["0.00", "+0.00", "+0.00"]);
  });

  it("keeps all ten persisted captions inside an 80px canvas", () => {
    const layout = layoutLeftoverMapPlot(
      [extendedPair()],
      (criterionCode) => criterionCode,
      { height: 80 },
    );

    expect(layout).not.toBeNull();
    expect(layout?.height).toBe(80);
    const segment = layout?.segments[0];
    expect(segment).toBeDefined();
    expect(segment?.labelY).toBeGreaterThanOrEqual(12);
    expect(segment?.reconstructionY).toBeGreaterThanOrEqual(segment?.labelY ?? 0);
    expect(segment?.explainedShareY).toBeGreaterThanOrEqual(segment?.reconstructionY ?? 0);
    expect(segment?.unexplainedShareY).toBeGreaterThanOrEqual(segment?.explainedShareY ?? 0);
    expect(segment?.crossShareY).toBeGreaterThanOrEqual(segment?.unexplainedShareY ?? 0);
    expect(segment?.unexplainedLeftoverY).toBeGreaterThanOrEqual(segment?.crossShareY ?? 0);
    expect(segment?.residualY).toBeGreaterThanOrEqual(segment?.unexplainedLeftoverY ?? 0);
    expect(segment?.observedY).toBeGreaterThanOrEqual(segment?.residualY ?? 0);
    expect(segment?.expectedY).toBeGreaterThanOrEqual(segment?.observedY ?? 0);
    expect(segment?.rankY).toBeGreaterThanOrEqual(segment?.expectedY ?? 0);
    expect(segment?.rankY).toBeLessThanOrEqual(76);
  });
});
