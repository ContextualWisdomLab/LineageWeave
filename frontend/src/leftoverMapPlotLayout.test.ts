import { describe, expect, it } from "vitest";
import type { LeftoverMapPlottablePair } from "./leftoverMapPlotLayout";
import {
  firstPlottablePairForPost,
  formatLeftoverMapDistance,
  hasLeftoverMapPlotCoordinates,
  layoutLeftoverMapPlot,
  PLOT_HEIGHT,
  PLOT_PADDING,
  PLOT_WIDTH,
} from "./leftoverMapPlotLayout";

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
    leftover_map_reconstruction: 0.248,
    leftover_map_explained_share: 0.76,
    ...overrides,
  };
}

function criterionLabel(code: string): string {
  return code === "sales_lead_quality" ? "sales-lead" : "negative";
}

describe("hasLeftoverMapPlotCoordinates", () => {
  it("requires four finite leftover-map coordinates", () => {
    expect(hasLeftoverMapPlotCoordinates(pair())).toBe(true);
    expect(hasLeftoverMapPlotCoordinates(pair({ leftover_map_person_axis_1: null }))).toBe(false);
    expect(hasLeftoverMapPlotCoordinates(pair({ leftover_map_item_axis_2: Number.NaN }))).toBe(false);
    expect(
      hasLeftoverMapPlotCoordinates(pair({ leftover_map_person_axis_2: Number.POSITIVE_INFINITY })),
    ).toBe(false);
  });
});

describe("layoutLeftoverMapPlot", () => {
  it("omits the plot when no pair has leftover-map coordinates", () => {
    expect(
      layoutLeftoverMapPlot(
        [pair({ leftover_map_person_axis_1: null, leftover_map_item_axis_1: null })],
        criterionLabel,
      ),
    ).toBeNull();
    expect(layoutLeftoverMapPlot([], criterionLabel)).toBeNull();
  });

  it("places persisted ξ and ζ without inventing a leftover score", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair(),
        pair({
          pair_kind: "farthest",
          post_id: "post-demo-spec",
          post_title: "Specification revision requested",
          criterion_code: "negative_sentiment",
          leftover_map_person_axis_1: 0.9,
          leftover_map_person_axis_2: 0.8,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
        }),
      ],
      criterionLabel,
    );
    expect(layout).not.toBeNull();
    expect(layout?.width).toBe(PLOT_WIDTH);
    expect(layout?.height).toBe(PLOT_HEIGHT);
    expect(layout?.persons).toHaveLength(2);
    expect(layout?.items).toHaveLength(2);
    expect(layout?.segments).toHaveLength(2);
    const publicPost = layout?.persons.find((marker) => marker.id === "post-demo-public");
    expect(publicPost).toMatchObject({ axis1: 0.5, axis2: 0.1, label: "Public post" });
    const salesLead = layout?.items.find((marker) => marker.id === "sales_lead_quality");
    expect(salesLead).toMatchObject({ axis1: 0.5, axis2: -0.02, label: "sales-lead" });
    expect(layout?.originX).toBeGreaterThan(PLOT_PADDING - 0.01);
    expect(layout?.originY).toBeLessThan(PLOT_HEIGHT - PLOT_PADDING + 0.01);
  });

  it("uses one centered isotropic scale for both leftover-map axes", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 0,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
        }),
        pair({
          pair_kind: "farthest",
          post_id: "post-demo-spec",
          criterion_code: "negative_sentiment",
          leftover_map_person_axis_1: 0,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 0,
          leftover_map_item_axis_2: 1,
        }),
      ],
      criterionLabel,
    );
    const horizontal = layout?.segments[0];
    const vertical = layout?.segments[1];
    expect(horizontal).toBeDefined();
    expect(vertical).toBeDefined();
    expect(Math.abs((horizontal?.x2 ?? 0) - (horizontal?.x1 ?? 0))).toBeCloseTo(
      Math.abs((vertical?.y2 ?? 0) - (vertical?.y1 ?? 0)),
      5,
    );
    expect(layout?.originX).toBeCloseTo(PLOT_WIDTH / 2 - (PLOT_HEIGHT - PLOT_PADDING * 2) / 2, 5);
    expect(layout?.originY).toBeCloseTo(PLOT_HEIGHT - PLOT_PADDING, 5);
  });

  it("plots a rank-0 origin cell at (0, 0) without inventing leftover structure", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 0,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 0,
          leftover_map_item_axis_2: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout).not.toBeNull();
    expect(layout?.persons[0]).toMatchObject({ axis1: 0, axis2: 0, x: layout?.originX, y: layout?.originY });
    expect(layout?.items[0]).toMatchObject({ axis1: 0, axis2: 0, x: layout?.originX, y: layout?.originY });
    expect(layout?.originX).toBeCloseTo(PLOT_WIDTH / 2, 5);
    expect(layout?.originY).toBeCloseTo(PLOT_HEIGHT / 2, 5);
  });

  it("deduplicates posts and criteria that appear on more than one pair", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair(),
        pair({
          pair_kind: "farthest",
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
        }),
      ],
      criterionLabel,
    );
    expect(layout?.persons).toHaveLength(1);
    expect(layout?.items).toHaveLength(2);
    expect(layout?.segments).toHaveLength(2);
  });

  it("skips a pair with any missing leftover-map coordinate instead of inventing one", () => {
    const layout = layoutLeftoverMapPlot(
      [pair(), pair({ post_id: "post-hidden-coord", leftover_map_item_axis_2: undefined })],
      criterionLabel,
    );
    expect(layout?.persons.map((marker) => marker.id)).toEqual(["post-demo-public"]);
    expect(layout?.segments).toHaveLength(1);
  });

  it("names persisted leftover-map coordinates as axis ticks without inventing a leftover score", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair(),
        pair({
          pair_kind: "farthest",
          post_id: "post-demo-spec",
          criterion_code: "negative_sentiment",
          leftover_map_person_axis_1: 0.9,
          leftover_map_person_axis_2: 0.8,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
        }),
      ],
      criterionLabel,
    );
    const axis1 = layout?.ticks.filter((tick) => tick.axis === 1).map((tick) => tick.label);
    const axis2 = layout?.ticks.filter((tick) => tick.axis === 2).map((tick) => tick.label);
    expect(axis1).toEqual(expect.arrayContaining(["0.00", "+0.50", "+0.90", "\u22120.70"]));
    expect(axis2).toEqual(expect.arrayContaining(["0.00", "+0.10", "\u22120.02", "+0.80", "\u22120.40"]));
    expect(axis1).toHaveLength(4);
    expect(axis2).toHaveLength(5);
    const originAxis1 = layout?.ticks.find((tick) => tick.axis === 1 && tick.value === 0);
    expect(originAxis1).toMatchObject({ x: layout?.originX, y: layout?.originY, label: "0.00" });
  });

  it("does not invent drawing-scale leftover-map ticks on a rank-0 origin cell", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 0,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 0,
          leftover_map_item_axis_2: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.ticks.map((tick) => tick.label)).toEqual(["0.00", "0.00"]);
    expect(layout?.ticks.every((tick) => tick.value === 0)).toBe(true);
    expect(layout?.ticks.some((tick) => tick.label === "+1.00" || tick.label === "\u22121.00")).toBe(
      false,
    );
  });

  it("keeps distinct persisted coordinates that share a rounded tick label", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 0.001,
          leftover_map_item_axis_1: 0.004,
        }),
      ],
      criterionLabel,
    );
    const axis1 = layout?.ticks.filter((tick) => tick.axis === 1);
    expect(axis1?.map((tick) => tick.value)).toEqual([0, 0.001, 0.004]);
    expect(axis1?.map((tick) => tick.label)).toEqual(["0.00", "+0.00", "+0.00"]);
    expect(new Set(axis1?.map((tick) => tick.x))).toHaveProperty("size", 3);
  });

  it("names persisted leftover-map distance on pair segments without inventing a leftover score", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair(),
        pair({
          pair_kind: "farthest",
          post_id: "post-demo-spec",
          criterion_code: "negative_sentiment",
          leftover_map_person_axis_1: 0.9,
          leftover_map_person_axis_2: 0.8,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          leftover_distance: 1.84,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.distanceLabel)).toEqual(["d 0.12", "d 1.84"]);
    expect(layout?.segments[0]?.labelX).toBeCloseTo(
      ((layout?.segments[0]?.x1 ?? 0) + (layout?.segments[0]?.x2 ?? 0)) / 2,
      5,
    );
  });

  it("omits a leftover-map distance caption when d is missing or non-finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ leftover_distance: null }),
        pair({
          pair_kind: "farthest",
          leftover_distance: Number.NaN,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.distanceLabel)).toEqual([null, null]);
  });

  it("does not invent leftover-map distance from plotted coordinates", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 0,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
          leftover_distance: 0.12,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.distanceLabel).toBe("d 0.12");
    expect(layout?.segments[0]?.distanceLabel).not.toBe("d 1.00");
  });

  it("names persisted leftover-map reconstruction on pair segments without inventing a leftover score", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair(),
        pair({
          pair_kind: "farthest",
          post_id: "post-demo-spec",
          criterion_code: "negative_sentiment",
          leftover_map_person_axis_1: 0.9,
          leftover_map_person_axis_2: 0.8,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          leftover_distance: 1.84,
          leftover_map_reconstruction: -0.95,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.reconstructionLabel)).toEqual([
      "R\u0302 +0.25",
      "R\u0302 \u22120.95",
    ]);
    expect(layout?.segments[0]?.reconstructionX).toBeCloseTo(layout?.segments[0]?.labelX ?? 0, 5);
    expect(layout?.segments[0]?.reconstructionY).toBeGreaterThan(layout?.segments[0]?.labelY ?? 0);
  });

  it("omits a leftover-map reconstruction caption when R̂ is missing or non-finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ leftover_map_reconstruction: null }),
        pair({
          pair_kind: "farthest",
          leftover_map_reconstruction: Number.NaN,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.reconstructionLabel)).toEqual([null, null]);
    expect(layout?.segments.map((segment) => segment.distanceLabel)).toEqual(["d 0.12", "d 0.12"]);
  });

  it("does not invent leftover-map reconstruction from plotted coordinates", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 1,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
          leftover_map_reconstruction: 0.35,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.reconstructionLabel).toBe("R\u0302 +0.35");
    expect(layout?.segments[0]?.reconstructionLabel).not.toBe("R\u0302 +1.00");
  });

  it("names rank-0 origin reconstruction R̂ 0.00 when that persisted value is finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 0,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 0,
          leftover_map_item_axis_2: 0,
          leftover_distance: 0,
          leftover_map_reconstruction: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.reconstructionLabel).toBe("R\u0302 0.00");
    expect(layout?.segments[0]?.distanceLabel).toBe("d 0.00");
  });

  it("names persisted leftover-map explained leftover share on pair segments without inventing a leftover score", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair(),
        pair({
          pair_kind: "farthest",
          post_id: "post-demo-spec",
          criterion_code: "negative_sentiment",
          leftover_map_person_axis_1: 0.9,
          leftover_map_person_axis_2: 0.8,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          leftover_distance: 1.84,
          leftover_map_reconstruction: -0.95,
          leftover_map_explained_share: 0.6,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.explainedShareLabel)).toEqual([
      "R\u0302\u00b2/R\u00b2 0.76",
      "R\u0302\u00b2/R\u00b2 0.60",
    ]);
    expect(layout?.segments[0]?.explainedShareX).toBeCloseTo(layout?.segments[0]?.labelX ?? 0, 5);
    expect(layout?.segments[0]?.explainedShareY).toBeGreaterThan(
      layout?.segments[0]?.reconstructionY ?? 0,
    );
  });

  it("omits a leftover-map explained leftover share caption when e is missing or non-finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ leftover_map_explained_share: null }),
        pair({
          pair_kind: "farthest",
          leftover_map_explained_share: Number.NaN,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.explainedShareLabel)).toEqual([null, null]);
    expect(layout?.segments.map((segment) => segment.reconstructionLabel)).toEqual([
      "R\u0302 +0.25",
      "R\u0302 +0.25",
    ]);
  });

  it("does not invent leftover-map explained leftover share from reconstruction or residual", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 1,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
          leftover_map_reconstruction: 1,
          leftover_map_explained_share: 0.76,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.explainedShareLabel).toBe("R\u0302\u00b2/R\u00b2 0.76");
    expect(layout?.segments[0]?.explainedShareLabel).not.toBe("R\u0302\u00b2/R\u00b2 1.00");
  });

  it("names rank-0 origin explained leftover share e 0.00 when that persisted value is finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 0,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 0,
          leftover_map_item_axis_2: 0,
          leftover_distance: 0,
          leftover_map_reconstruction: 0,
          leftover_map_explained_share: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.explainedShareLabel).toBe("R\u0302\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.reconstructionLabel).toBe("R\u0302 0.00");
    expect(layout?.segments[0]?.distanceLabel).toBe("d 0.00");
  });
});

describe("formatLeftoverMapDistance", () => {
  it("formats persisted leftover-map distance without inventing a leftover score", () => {
    expect(formatLeftoverMapDistance(0.12)).toBe("d 0.12");
    expect(formatLeftoverMapDistance(0)).toBe("d 0.00");
    expect(formatLeftoverMapDistance(null)).toBeNull();
    expect(formatLeftoverMapDistance(Number.NaN)).toBeNull();
  });
});

describe("firstPlottablePairForPost", () => {
  it("returns the first leftover pair whose coordinates can open that post", () => {
    const closest = pair();
    const farthest = pair({ pair_kind: "farthest", leftover_map_item_axis_1: -0.2 });
    expect(firstPlottablePairForPost([closest, farthest], "post-demo-public")).toBe(closest);
    expect(firstPlottablePairForPost([pair({ leftover_map_person_axis_1: null })], "post-demo-public")).toBeNull();
  });
});
