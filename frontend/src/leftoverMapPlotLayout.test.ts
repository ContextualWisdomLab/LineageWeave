import { describe, expect, it } from "vitest";
import type { LeftoverMapPlottablePair } from "./leftoverMapPlotLayout";
import {
  firstPlottablePairForPost,
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
});

describe("firstPlottablePairForPost", () => {
  it("returns the first leftover pair whose coordinates can open that post", () => {
    const closest = pair();
    const farthest = pair({ pair_kind: "farthest", leftover_map_item_axis_1: -0.2 });
    expect(firstPlottablePairForPost([closest, farthest], "post-demo-public")).toBe(closest);
    expect(firstPlottablePairForPost([pair({ leftover_map_person_axis_1: null })], "post-demo-public")).toBeNull();
  });
});
