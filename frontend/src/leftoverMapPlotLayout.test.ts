import { describe, expect, it } from "vitest";
import type { LeftoverMapPlottablePair } from "./leftoverMapPlotLayout";
import {
  firstPlottablePairForPost,
  formatLeftoverMapDistance,
  hasLeftoverMapPlotCoordinates,
  layoutLeftoverMapPlot,
  LEFTOVER_MAP_COMPARE_PLOT_CAPTION,
  LEFTOVER_MAP_COMPARE_PLOT_LABEL,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RECONSTRUCTION,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPLAINED_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_CROSS_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_OBSERVED,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_DISTANCE,
  LEFTOVER_MAP_COMPARE_PLOT_TICK,
  LEFTOVER_MAP_COMPARE_PLOT_SVG,
  LEFTOVER_MAP_PLOT_TICK,
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
    leftover_map_unexplained_share: 0.02,
    leftover_map_cross_share: 0.12,
    leftover_map_unexplained: 0.05,
    leftover_residual: 0.4,
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

  it("names persisted leftover-map unexplained leftover share on pair segments without inventing a leftover score", () => {
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
          leftover_map_unexplained_share: 0.05,
          leftover_map_cross_share: -0.24,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.unexplainedShareLabel)).toEqual([
      "U\u00b2/R\u00b2 0.02",
      "U\u00b2/R\u00b2 0.05",
    ]);
    expect(layout?.segments[0]?.unexplainedShareX).toBeCloseTo(layout?.segments[0]?.labelX ?? 0, 5);
    expect(layout?.segments[0]?.unexplainedShareY).toBeGreaterThan(
      layout?.segments[0]?.explainedShareY ?? 0,
    );
  });

  it("omits a leftover-map unexplained leftover share caption when s is missing or non-finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ leftover_map_unexplained_share: null }),
        pair({
          pair_kind: "farthest",
          leftover_map_unexplained_share: Number.NaN,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.unexplainedShareLabel)).toEqual([null, null]);
    expect(layout?.segments.map((segment) => segment.explainedShareLabel)).toEqual([
      "R\u0302\u00b2/R\u00b2 0.76",
      "R\u0302\u00b2/R\u00b2 0.76",
    ]);
  });

  it("does not invent leftover-map unexplained leftover share from unexplained leftover or residual", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 1,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
          leftover_map_reconstruction: 1,
          leftover_map_explained_share: 0.76,
          leftover_map_unexplained_share: 0.02,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.unexplainedShareLabel).toBe("U\u00b2/R\u00b2 0.02");
    expect(layout?.segments[0]?.unexplainedShareLabel).not.toBe("U\u00b2/R\u00b2 1.00");
  });

  it("names rank-0 origin unexplained leftover share s 0.00 when that persisted value is finite", () => {
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
          leftover_map_unexplained_share: 0,
          leftover_map_cross_share: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.unexplainedShareLabel).toBe("U\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.explainedShareLabel).toBe("R\u0302\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.reconstructionLabel).toBe("R\u0302 0.00");
    expect(layout?.segments[0]?.distanceLabel).toBe("d 0.00");
  });

  it("names persisted leftover-map cross share on pair segments without inventing a leftover score", () => {
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
          leftover_map_unexplained_share: 0.05,
          leftover_map_cross_share: -0.24,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.crossShareLabel)).toEqual([
      "2R\u0302U/R\u00b2 0.12",
      "2R\u0302U/R\u00b2 -0.24",
    ]);
    expect(layout?.segments[0]?.crossShareX).toBeCloseTo(layout?.segments[0]?.labelX ?? 0, 5);
    expect(layout?.segments[0]?.crossShareY).toBeGreaterThan(
      layout?.segments[0]?.unexplainedShareY ?? 0,
    );
  });

  it("omits a leftover-map cross share caption when x is missing or non-finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ leftover_map_cross_share: null }),
        pair({
          pair_kind: "farthest",
          leftover_map_cross_share: Number.NaN,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.crossShareLabel)).toEqual([null, null]);
    expect(layout?.segments.map((segment) => segment.unexplainedShareLabel)).toEqual([
      "U\u00b2/R\u00b2 0.02",
      "U\u00b2/R\u00b2 0.02",
    ]);
  });

  it("does not invent leftover-map cross share from reconstruction or residual", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 1,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
          leftover_map_reconstruction: 1,
          leftover_map_explained_share: 0.76,
          leftover_map_unexplained_share: 0.02,
          leftover_map_cross_share: 0.12,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.crossShareLabel).toBe("2R\u0302U/R\u00b2 0.12");
    expect(layout?.segments[0]?.crossShareLabel).not.toBe("2R\u0302U/R\u00b2 1.00");
  });

  it("names rank-0 origin leftover-map cross share x 0.00 when that persisted value is finite", () => {
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
          leftover_map_unexplained_share: 0,
          leftover_map_cross_share: 0,
          leftover_map_unexplained: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.crossShareLabel).toBe("2R\u0302U/R\u00b2 0.00");
    expect(layout?.segments[0]?.unexplainedLeftoverLabel).toBe("U 0.00");
    expect(layout?.segments[0]?.unexplainedShareLabel).toBe("U\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.explainedShareLabel).toBe("R\u0302\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.reconstructionLabel).toBe("R\u0302 0.00");
    expect(layout?.segments[0]?.distanceLabel).toBe("d 0.00");
  });

  it("names persisted leftover-map unexplained leftover on pair segments without inventing a leftover score", () => {
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
          leftover_map_unexplained_share: 0.05,
          leftover_map_cross_share: -0.24,
          leftover_map_unexplained: -0.25,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.unexplainedLeftoverLabel)).toEqual([
      "U +0.05",
      "U \u22120.25",
    ]);
    expect(layout?.segments[0]?.unexplainedLeftoverX).toBeCloseTo(layout?.segments[0]?.labelX ?? 0, 5);
    expect(layout?.segments[0]?.unexplainedLeftoverY).toBeGreaterThan(
      layout?.segments[0]?.crossShareY ?? 0,
    );
  });

  it("omits a leftover-map unexplained leftover caption when U is missing or non-finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ leftover_map_unexplained: null }),
        pair({
          pair_kind: "farthest",
          leftover_map_unexplained: Number.NaN,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.unexplainedLeftoverLabel)).toEqual([null, null]);
    expect(layout?.segments.map((segment) => segment.crossShareLabel)).toEqual([
      "2R\u0302U/R\u00b2 0.12",
      "2R\u0302U/R\u00b2 0.12",
    ]);
  });

  it("does not invent leftover-map unexplained leftover from reconstruction or residual", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 1,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
          leftover_map_reconstruction: 1,
          leftover_map_explained_share: 0.76,
          leftover_map_unexplained_share: 0.02,
          leftover_map_cross_share: 0.12,
          leftover_map_unexplained: 0.05,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.unexplainedLeftoverLabel).toBe("U +0.05");
    expect(layout?.segments[0]?.unexplainedLeftoverLabel).not.toBe("U +0.15");
  });

  it("names rank-0 origin unexplained leftover U 0.00 when that persisted value is finite", () => {
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
          leftover_map_unexplained_share: 0,
          leftover_map_cross_share: 0,
          leftover_map_unexplained: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.unexplainedLeftoverLabel).toBe("U 0.00");
    expect(layout?.segments[0]?.crossShareLabel).toBe("2R\u0302U/R\u00b2 0.00");
    expect(layout?.segments[0]?.unexplainedShareLabel).toBe("U\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.explainedShareLabel).toBe("R\u0302\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.reconstructionLabel).toBe("R\u0302 0.00");
    expect(layout?.segments[0]?.distanceLabel).toBe("d 0.00");
  });

  it("names persisted leftover residual on pair segments without inventing a leftover score", () => {
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
          leftover_map_unexplained_share: 0.05,
          leftover_map_cross_share: -0.24,
          leftover_map_unexplained: -0.25,
          leftover_residual: -1.1,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.residualLabel)).toEqual([
      "R +0.40",
      "R \u22121.10",
    ]);
    expect(layout?.segments[0]?.residualX).toBeCloseTo(layout?.segments[0]?.labelX ?? 0, 5);
    expect(layout?.segments[0]?.residualY).toBeGreaterThan(
      layout?.segments[0]?.unexplainedLeftoverY ?? 0,
    );
  });

  it("omits a leftover residual caption when R is missing or non-finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ leftover_residual: null }),
        pair({
          pair_kind: "farthest",
          leftover_residual: Number.NaN,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.residualLabel)).toEqual([null, null]);
    expect(layout?.segments.map((segment) => segment.unexplainedLeftoverLabel)).toEqual([
      "U +0.05",
      "U +0.05",
    ]);
  });

  it("does not invent leftover residual from unexplained leftover or reconstruction", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 1,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
          leftover_map_reconstruction: 1,
          leftover_map_explained_share: 0.76,
          leftover_map_unexplained_share: 0.02,
          leftover_map_cross_share: 0.12,
          leftover_map_unexplained: 0.05,
          leftover_residual: 0.4,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.residualLabel).toBe("R +0.40");
    expect(layout?.segments[0]?.residualLabel).not.toBe("R +1.05");
  });

  it("names rank-0 origin leftover residual R 0.00 when that persisted value is finite", () => {
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
          leftover_map_unexplained_share: 0,
          leftover_map_cross_share: 0,
          leftover_map_unexplained: 0,
          leftover_residual: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.residualLabel).toBe("R 0.00");
    expect(layout?.segments[0]?.unexplainedLeftoverLabel).toBe("U 0.00");
    expect(layout?.segments[0]?.crossShareLabel).toBe("2R\u0302U/R\u00b2 0.00");
    expect(layout?.segments[0]?.unexplainedShareLabel).toBe("U\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.explainedShareLabel).toBe("R\u0302\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.reconstructionLabel).toBe("R\u0302 0.00");
    expect(layout?.segments[0]?.distanceLabel).toBe("d 0.00");
  });

  it("names persisted leftover observed on pair segments without inventing a leftover score", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ observed_response: 2.4 }),
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
          leftover_map_unexplained_share: 0.05,
          leftover_map_cross_share: -0.24,
          leftover_map_unexplained: -0.25,
          leftover_residual: -1.1,
          observed_response: 0.9,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.observedLabel)).toEqual([
      "Y 2.40",
      "Y 0.90",
    ]);
    expect(layout?.segments[0]?.observedX).toBeCloseTo(layout?.segments[0]?.labelX ?? 0, 5);
    expect(layout?.segments[0]?.observedY).toBeGreaterThan(
      layout?.segments[0]?.residualY ?? 0,
    );
  });

  it("omits a leftover observed caption when Y is missing or non-finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ observed_response: null }),
        pair({
          pair_kind: "farthest",
          observed_response: Number.NaN,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.observedLabel)).toEqual([null, null]);
    expect(layout?.segments.map((segment) => segment.residualLabel)).toEqual([
      "R +0.40",
      "R +0.40",
    ]);
  });

  it("does not invent leftover observed from residual and expected", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 1,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
          leftover_map_reconstruction: 1,
          leftover_map_explained_share: 0.76,
          leftover_map_unexplained_share: 0.02,
          leftover_map_cross_share: 0.12,
          leftover_map_unexplained: 0.05,
          leftover_residual: 0.4,
          observed_response: 9.9,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.observedLabel).toBe("Y 9.90");
    expect(layout?.segments[0]?.observedLabel).not.toBe("Y 2.40");
  });

  it("names rank-0 origin leftover observed Y 0.00 when that persisted value is finite", () => {
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
          leftover_map_unexplained_share: 0,
          leftover_map_cross_share: 0,
          leftover_map_unexplained: 0,
          leftover_residual: 0,
          observed_response: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.observedLabel).toBe("Y 0.00");
    expect(layout?.segments[0]?.residualLabel).toBe("R 0.00");
    expect(layout?.segments[0]?.unexplainedLeftoverLabel).toBe("U 0.00");
    expect(layout?.segments[0]?.crossShareLabel).toBe("2R\u0302U/R\u00b2 0.00");
    expect(layout?.segments[0]?.unexplainedShareLabel).toBe("U\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.explainedShareLabel).toBe("R\u0302\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.reconstructionLabel).toBe("R\u0302 0.00");
    expect(layout?.segments[0]?.distanceLabel).toBe("d 0.00");
  });

  it("names persisted leftover expected on pair segments without inventing a leftover score", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ observed_response: 2.4, expected_response: 2.0 }),
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
          leftover_map_unexplained_share: 0.05,
          leftover_map_cross_share: -0.24,
          leftover_map_unexplained: -0.25,
          leftover_residual: -1.1,
          observed_response: 0.9,
          expected_response: 2.0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.expectedLabel)).toEqual([
      "E 2.00",
      "E 2.00",
    ]);
    expect(layout?.segments[0]?.expectedX).toBeCloseTo(layout?.segments[0]?.labelX ?? 0, 5);
    expect(layout?.segments[0]?.expectedY).toBeGreaterThan(
      layout?.segments[0]?.observedY ?? 0,
    );
  });

  it("omits a leftover expected caption when E is missing or non-finite", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ observed_response: 2.4, expected_response: null }),
        pair({
          pair_kind: "farthest",
          observed_response: 2.4,
          expected_response: Number.NaN,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.expectedLabel)).toEqual([null, null]);
    expect(layout?.segments.map((segment) => segment.observedLabel)).toEqual([
      "Y 2.40",
      "Y 2.40",
    ]);
  });

  it("does not invent leftover expected from observed and residual", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 1,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
          leftover_map_reconstruction: 1,
          leftover_map_explained_share: 0.76,
          leftover_map_unexplained_share: 0.02,
          leftover_map_cross_share: 0.12,
          leftover_map_unexplained: 0.05,
          leftover_residual: 0.4,
          observed_response: 2.4,
          expected_response: 9.9,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.expectedLabel).toBe("E 9.90");
    expect(layout?.segments[0]?.expectedLabel).not.toBe("E 2.00");
  });

  it("names rank-0 origin leftover expected E 0.00 when that persisted value is finite", () => {
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
          leftover_map_unexplained_share: 0,
          leftover_map_cross_share: 0,
          leftover_map_unexplained: 0,
          leftover_residual: 0,
          observed_response: 0,
          expected_response: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.expectedLabel).toBe("E 0.00");
    expect(layout?.segments[0]?.observedLabel).toBe("Y 0.00");
    expect(layout?.segments[0]?.residualLabel).toBe("R 0.00");
    expect(layout?.segments[0]?.unexplainedLeftoverLabel).toBe("U 0.00");
    expect(layout?.segments[0]?.crossShareLabel).toBe("2R\u0302U/R\u00b2 0.00");
    expect(layout?.segments[0]?.unexplainedShareLabel).toBe("U\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.explainedShareLabel).toBe("R\u0302\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.reconstructionLabel).toBe("R\u0302 0.00");
    expect(layout?.segments[0]?.distanceLabel).toBe("d 0.00");
  });

  it("names persisted leftover-map rank on pair segments without inventing leftover structure", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ leftover_map_rank: 1, observed_response: 2.4, expected_response: 2.0 }),
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
          leftover_map_unexplained_share: 0.05,
          leftover_map_cross_share: -0.24,
          leftover_map_unexplained: -0.25,
          leftover_residual: -1.1,
          observed_response: 0.9,
          expected_response: 2.0,
          leftover_map_rank: 1,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.rankLabel)).toEqual([
      "rank 1",
      "rank 1",
    ]);
    expect(layout?.segments[0]?.rankX).toBeCloseTo(layout?.segments[0]?.labelX ?? 0, 5);
    expect(layout?.segments[0]?.rankY).toBeGreaterThan(
      layout?.segments[0]?.expectedY ?? 0,
    );
  });

  it("omits a leftover-map rank caption when rank is missing or not a non-negative integer", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({ leftover_map_rank: null, expected_response: 2.0 }),
        pair({
          pair_kind: "farthest",
          leftover_map_rank: Number.NaN,
          leftover_map_item_axis_1: -0.7,
          leftover_map_item_axis_2: -0.4,
          criterion_code: "negative_sentiment",
          expected_response: 2.0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments.map((segment) => segment.rankLabel)).toEqual([null, null]);
    expect(layout?.segments.map((segment) => segment.expectedLabel)).toEqual([
      "E 2.00",
      "E 2.00",
    ]);
  });

  it("does not invent leftover-map rank from plotted coordinates", () => {
    const layout = layoutLeftoverMapPlot(
      [
        pair({
          leftover_map_person_axis_1: 1,
          leftover_map_person_axis_2: 0,
          leftover_map_item_axis_1: 1,
          leftover_map_item_axis_2: 0,
          leftover_map_reconstruction: 1,
          leftover_map_explained_share: 0.76,
          leftover_map_unexplained_share: 0.02,
          leftover_map_cross_share: 0.12,
          leftover_map_unexplained: 0.05,
          leftover_residual: 0.4,
          observed_response: 2.4,
          expected_response: 2.0,
          leftover_map_rank: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.rankLabel).toBe("rank 0");
    expect(layout?.segments[0]?.rankLabel).not.toBe("rank 2");
    expect(layout?.segments[0]?.rankLabel).not.toBe("rank 1");
  });

  it("names rank-0 origin leftover-map rank 0 when that persisted value is a non-negative integer", () => {
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
          leftover_map_unexplained_share: 0,
          leftover_map_cross_share: 0,
          leftover_map_unexplained: 0,
          leftover_residual: 0,
          observed_response: 0,
          expected_response: 0,
          leftover_map_rank: 0,
        }),
      ],
      criterionLabel,
    );
    expect(layout?.segments[0]?.rankLabel).toBe("rank 0");
    expect(layout?.segments[0]?.expectedLabel).toBe("E 0.00");
    expect(layout?.segments[0]?.observedLabel).toBe("Y 0.00");
    expect(layout?.segments[0]?.residualLabel).toBe("R 0.00");
    expect(layout?.segments[0]?.unexplainedLeftoverLabel).toBe("U 0.00");
    expect(layout?.segments[0]?.crossShareLabel).toBe("2R\u0302U/R\u00b2 0.00");
    expect(layout?.segments[0]?.unexplainedShareLabel).toBe("U\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.explainedShareLabel).toBe("R\u0302\u00b2/R\u00b2 0.00");
    expect(layout?.segments[0]?.reconstructionLabel).toBe("R\u0302 0.00");
    expect(layout?.segments[0]?.distanceLabel).toBe("d 0.00");
  });
});

describe("formatLeftoverMapDistance", () => {
  it("formats persisted leftover-map distance without inventing a leftover score", () => {
    expect(formatLeftoverMapDistance(0.12)).toBe("d 0.12");
    expect(formatLeftoverMapDistance(0)).toBe("d 0.00");
    expect(formatLeftoverMapDistance(1.84)).toBe("d 1.84");
    expect(formatLeftoverMapDistance(-0.05)).toBe("d -0.05");
    expect(formatLeftoverMapDistance(null)).toBeNull();
    expect(formatLeftoverMapDistance(Number.NaN)).toBeNull();
    expect(formatLeftoverMapDistance(Number.POSITIVE_INFINITY)).toBeNull();
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

describe("leftover map comparison graphic labels", () => {
  it("stays distinct from leftover-map graphic display copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_LABEL).toBe("Leftover map comparison graphic");
    expect(LEFTOVER_MAP_COMPARE_PLOT_SVG).toBe("Leftover map comparison");
    expect(LEFTOVER_MAP_COMPARE_PLOT_CAPTION).toContain("already-named coordinates");
    expect(LEFTOVER_MAP_COMPARE_PLOT_LABEL).not.toBe("Leftover-map graphic display");
    expect(LEFTOVER_MAP_COMPARE_PLOT_SVG).not.toBe("Leftover map");
  });

  it("stays distinct from leftover-map reconstruction copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RECONSTRUCTION).toBe(
      "leftover map comparison graphic reconstruction {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RECONSTRUCTION).not.toBe(
      "leftover-map reconstruction {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RECONSTRUCTION).not.toBe(
      "Leftover map comparison reconstruction",
    );
  });

  it("stays distinct from leftover-map explained leftover share copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPLAINED_SHARE).toBe(
      "leftover map comparison graphic explained leftover share {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPLAINED_SHARE).not.toBe(
      "leftover-map explained leftover share {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPLAINED_SHARE).not.toBe(
      "Leftover map comparison explained leftover share",
    );
  });

  it("stays distinct from leftover-map unexplained leftover share copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED_SHARE).toBe(
      "leftover map comparison graphic unexplained leftover share {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED_SHARE).not.toBe(
      "leftover-map unexplained leftover share {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED_SHARE).not.toBe(
      "Leftover map comparison unexplained leftover share",
    );
  });

  it("stays distinct from leftover-map cross share copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_CROSS_SHARE).toBe(
      "leftover map comparison graphic cross share {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_CROSS_SHARE).not.toBe(
      "leftover-map cross share {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_CROSS_SHARE).not.toBe(
      "Leftover map comparison cross share",
    );
  });

  it("stays distinct from leftover-map unexplained leftover copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED).toBe(
      "leftover map comparison graphic unexplained leftover {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED).not.toBe(
      "leftover-map unexplained leftover {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED).not.toBe(
      "Leftover map comparison unexplained leftover",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED_SHARE,
    );
  });

  it("stays distinct from leftover residual copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL).toBe(
      "leftover map comparison graphic leftover residual {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL).not.toBe(
      "leftover residual {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL).not.toBe(
      "Leftover map comparison residual",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED,
    );
  });

  it("stays distinct from leftover observed copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_OBSERVED).toBe(
      "leftover map comparison graphic leftover observed {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_OBSERVED).not.toBe(
      "leftover observed {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_OBSERVED).not.toBe(
      "Leftover map comparison observed",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_OBSERVED).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL,
    );
  });

  it("stays distinct from leftover expected copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED).toBe(
      "leftover map comparison graphic leftover expected {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED).not.toBe(
      "leftover expected {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED).not.toBe(
      "Leftover map comparison expected",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_OBSERVED,
    );
  });

  it("stays distinct from leftover-map rank copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK).toBe(
      "leftover map comparison graphic leftover-map rank {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK).not.toBe(
      "leftover-map rank {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK).not.toBe(
      "Leftover map comparison rank",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED,
    );
  });

  it("stays distinct from leftover-map distance copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_DISTANCE).toBe(
      "leftover map comparison graphic leftover-map distance {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_DISTANCE).not.toBe(
      "leftover-map distance {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_DISTANCE).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK,
    );
  });

  it("stays distinct from leftover-map coordinate tick copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).toBe(
      "leftover map comparison graphic leftover-map axis {axis} tick {value}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe(
      "leftover-map axis {axis} tick {value}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe(LEFTOVER_MAP_PLOT_TICK);
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe(
      "leftover map comparison axis {axis} ({share}%)",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe(
      "leftover map comparison graphic leftover-map axis {axis} σ {value}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe("leftover-map axis {axis} σ {value}");
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe("leftover axis {axis} σ {value}");
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe("leftover-map axis {axis} tick {value} σ {singular}");
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe(
      "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe(
      "leftover map comparison leftover axis {axis} σ {value}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe(
      "leftover map comparison leftover axis {axis} tick {value}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe(
      "leftover map comparison leftover axis {axis} tick {value} σ {singular}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe("leftover axis {axis} tick {value}");
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe("leftover axis {axis} tick {value} σ {singular}");
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_DISTANCE,
    );
  });
});
