import { describe, expect, it } from "vitest";
import { layoutLeftoverMapPlot, type LeftoverMapPlottablePair } from "./leftoverMapPlotLayout";

const completeCaptionPair: LeftoverMapPlottablePair = {
  pair_kind: "closest",
  post_id: "post-small-canvas",
  post_title: "Small canvas post",
  criterion_code: "sales_lead_quality",
  leftover_distance: 0.12,
  leftover_map_reconstruction: 0.25,
  leftover_map_explained_share: 0.76,
  leftover_map_person_axis_1: -1,
  leftover_map_person_axis_2: -1,
  leftover_map_item_axis_1: 1,
  leftover_map_item_axis_2: -1,
};

describe("layoutLeftoverMapPlot small-canvas caption bounds", () => {
  it("keeps a complete three-caption stack inside the requested 20px height", () => {
    const layout = layoutLeftoverMapPlot(
      [completeCaptionPair],
      (criterionCode) => criterionCode,
      { height: 20 },
    );

    expect(layout).not.toBeNull();
    expect(layout?.height).toBe(20);
    const segment = layout?.segments[0];
    expect(segment).toBeDefined();
    expect(segment?.labelY).toBeGreaterThanOrEqual(12);
    expect(segment?.reconstructionY).toBeGreaterThanOrEqual(segment?.labelY ?? 0);
    expect(segment?.explainedShareY).toBeGreaterThanOrEqual(segment?.reconstructionY ?? 0);
    expect(segment?.explainedShareY).toBeLessThanOrEqual(16);
  });
});
