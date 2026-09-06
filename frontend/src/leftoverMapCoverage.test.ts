import { describe, expect, it } from "vitest";
import type { LeftoverMapCoverage } from "./api";
import {
  leftoverMapCoverageCounts,
  leftoverMapIncompleteItemCount,
  leftoverMapIncompletePostCount,
  leftoverMapItemCoverageCounts,
  LEFTOVER_MAP_COMPARE_COVERAGE_LABEL,
  LEFTOVER_MAP_COMPARE_ITEM_COVERAGE_LABEL,
  LEFTOVER_MAP_COMPARE_INCOMPLETE_POST_LABEL,
  LEFTOVER_MAP_COMPARE_INCOMPLETE_ITEM_LABEL,
  LEFTOVER_MAP_COMPARE_PLOT_COVERAGE_LABEL,
  LEFTOVER_MAP_COMPARE_PLOT_ITEM_COVERAGE_LABEL,
  LEFTOVER_MAP_LIST_COVERAGE_LABEL,
  LEFTOVER_MAP_LIST_INCOMPLETE_ITEM_LABEL,
  LEFTOVER_MAP_LIST_INCOMPLETE_POST_LABEL,
  LEFTOVER_MAP_LIST_ITEM_COVERAGE_LABEL,
  LEFTOVER_MAP_PLOT_COVERAGE_LABEL,
  LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM_LABEL,
  LEFTOVER_MAP_PLOT_INCOMPLETE_POST_LABEL,
  LEFTOVER_MAP_PLOT_ITEM_COVERAGE_LABEL,
} from "./leftoverMapCoverage";

function coverage(overrides: Partial<LeftoverMapCoverage> = {}): LeftoverMapCoverage {
  return {
    map_post_count: 2,
    scored_post_count: 3,
    map_item_count: 2,
    scored_item_count: 2,
    incomplete_post_count: 1,
    incomplete_item_count: 0,
    ...overrides,
  };
}

describe("leftoverMapCoverageCounts", () => {
  it("names persisted leftover-map complete-case coverage without inventing a leftover score", () => {
    expect(leftoverMapCoverageCounts(coverage())).toEqual({ used: 2, scored: 3 });
    expect(leftoverMapCoverageCounts(coverage({ map_post_count: 0 }))).toEqual({
      used: 0,
      scored: 3,
    });
    expect(leftoverMapCoverageCounts(coverage({ map_post_count: 3, incomplete_post_count: 0 }))).toEqual({
      used: 3,
      scored: 3,
    });
  });

  it("omits coverage when counts are missing or not usable complete-case integers", () => {
    expect(leftoverMapCoverageCounts(null)).toBeNull();
    expect(leftoverMapCoverageCounts(undefined)).toBeNull();
    expect(leftoverMapCoverageCounts(coverage({ map_post_count: -1 }))).toBeNull();
    expect(leftoverMapCoverageCounts(coverage({ scored_post_count: 0 }))).toBeNull();
    expect(leftoverMapCoverageCounts(coverage({ map_post_count: 4 }))).toBeNull();
    expect(leftoverMapCoverageCounts(coverage({ map_post_count: 1.5 }))).toBeNull();
    expect(leftoverMapCoverageCounts(coverage({ scored_post_count: Number.NaN }))).toBeNull();
  });

  it("does not invent leftover-map coverage from plotted marker count", () => {
    expect(
      leftoverMapCoverageCounts(
        coverage({
          map_post_count: 2,
          scored_post_count: 3,
        }),
      ),
    ).toEqual({ used: 2, scored: 3 });
    expect(leftoverMapCoverageCounts(coverage({ map_post_count: 2, scored_post_count: 3 }))).not.toEqual({
      used: 2,
      scored: 2,
    });
  });

  it("keeps the pair-list coverage label distinct from the graphic coverage label", () => {
    expect(LEFTOVER_MAP_LIST_COVERAGE_LABEL).toBe("Leftover map coverage");
    expect(LEFTOVER_MAP_PLOT_COVERAGE_LABEL).toBe("Leftover-map graphic coverage");
    expect(LEFTOVER_MAP_LIST_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_PLOT_COVERAGE_LABEL);
  });

  it("keeps the grouping comparison coverage label distinct from the pair-list and graphic labels", () => {
    expect(LEFTOVER_MAP_COMPARE_COVERAGE_LABEL).toBe("Leftover map comparison coverage");
    expect(LEFTOVER_MAP_COMPARE_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_LIST_COVERAGE_LABEL);
    expect(LEFTOVER_MAP_COMPARE_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_PLOT_COVERAGE_LABEL);
  });

  it("keeps the grouping comparison graphic coverage label distinct from the pair-list, graphic, and strip labels", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_COVERAGE_LABEL).toBe("Leftover map comparison graphic coverage");
    expect(LEFTOVER_MAP_COMPARE_PLOT_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_LIST_COVERAGE_LABEL);
    expect(LEFTOVER_MAP_COMPARE_PLOT_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_PLOT_COVERAGE_LABEL);
    expect(LEFTOVER_MAP_COMPARE_PLOT_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_COMPARE_COVERAGE_LABEL);
  });
});

describe("leftoverMapItemCoverageCounts", () => {
  it("names persisted leftover-map item complete-case coverage without inventing a leftover score", () => {
    expect(leftoverMapItemCoverageCounts(coverage())).toEqual({ used: 2, scored: 2 });
    expect(leftoverMapItemCoverageCounts(coverage({ map_item_count: 0, scored_item_count: 2 }))).toEqual({
      used: 0,
      scored: 2,
    });
    expect(
      leftoverMapItemCoverageCounts(coverage({ map_item_count: 1, scored_item_count: 2, incomplete_item_count: 1 })),
    ).toEqual({ used: 1, scored: 2 });
  });

  it("omits item coverage when counts are missing or not usable complete-case integers", () => {
    expect(leftoverMapItemCoverageCounts(null)).toBeNull();
    expect(leftoverMapItemCoverageCounts(undefined)).toBeNull();
    expect(leftoverMapItemCoverageCounts(coverage({ map_item_count: -1 }))).toBeNull();
    expect(leftoverMapItemCoverageCounts(coverage({ scored_item_count: 0 }))).toBeNull();
    expect(leftoverMapItemCoverageCounts(coverage({ map_item_count: 3, scored_item_count: 2 }))).toBeNull();
    expect(leftoverMapItemCoverageCounts(coverage({ map_item_count: 1.5 }))).toBeNull();
    expect(leftoverMapItemCoverageCounts(coverage({ scored_item_count: Number.NaN }))).toBeNull();
  });

  it("does not invent leftover-map item coverage from plotted criterion marker count", () => {
    expect(
      leftoverMapItemCoverageCounts(
        coverage({
          map_item_count: 1,
          scored_item_count: 2,
        }),
      ),
    ).toEqual({ used: 1, scored: 2 });
    expect(leftoverMapItemCoverageCounts(coverage({ map_item_count: 1, scored_item_count: 2 }))).not.toEqual({
      used: 2,
      scored: 2,
    });
  });

  it("keeps the pair-list item coverage label distinct from the graphic item coverage label", () => {
    expect(LEFTOVER_MAP_LIST_ITEM_COVERAGE_LABEL).toBe("Leftover map item coverage");
    expect(LEFTOVER_MAP_PLOT_ITEM_COVERAGE_LABEL).toBe("Leftover-map graphic item coverage");
    expect(LEFTOVER_MAP_LIST_ITEM_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_PLOT_ITEM_COVERAGE_LABEL);
  });

  it("keeps the grouping comparison item coverage label distinct from the pair-list and graphic item labels", () => {
    expect(LEFTOVER_MAP_COMPARE_ITEM_COVERAGE_LABEL).toBe("Leftover map comparison item coverage");
    expect(LEFTOVER_MAP_COMPARE_ITEM_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_LIST_ITEM_COVERAGE_LABEL);
    expect(LEFTOVER_MAP_COMPARE_ITEM_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_PLOT_ITEM_COVERAGE_LABEL);
  });

  it("keeps the grouping comparison graphic item coverage label distinct from the pair-list, graphic, strip, and comparison graphic coverage labels", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_ITEM_COVERAGE_LABEL).toBe(
      "Leftover map comparison graphic item coverage",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_ITEM_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_LIST_ITEM_COVERAGE_LABEL);
    expect(LEFTOVER_MAP_COMPARE_PLOT_ITEM_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_PLOT_ITEM_COVERAGE_LABEL);
    expect(LEFTOVER_MAP_COMPARE_PLOT_ITEM_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_COMPARE_ITEM_COVERAGE_LABEL);
    expect(LEFTOVER_MAP_COMPARE_PLOT_ITEM_COVERAGE_LABEL).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_COVERAGE_LABEL);
  });
});

describe("leftoverMapIncompletePostCount", () => {
  it("names persisted leftover-map incomplete post coverage without inventing a leftover score", () => {
    expect(leftoverMapIncompletePostCount(coverage())).toEqual({ dropped: 1 });
    expect(
      leftoverMapIncompletePostCount(coverage({ map_post_count: 0, incomplete_post_count: 3 })),
    ).toEqual({ dropped: 3 });
    expect(
      leftoverMapIncompletePostCount(coverage({ map_post_count: 3, incomplete_post_count: 0 })),
    ).toEqual({ dropped: 0 });
  });

  it("omits incomplete post coverage when the dropped count is missing or not a usable integer", () => {
    expect(leftoverMapIncompletePostCount(null)).toBeNull();
    expect(leftoverMapIncompletePostCount(undefined)).toBeNull();
    expect(leftoverMapIncompletePostCount(coverage({ incomplete_post_count: -1 }))).toBeNull();
    expect(leftoverMapIncompletePostCount(coverage({ incomplete_post_count: 1.5 }))).toBeNull();
    expect(leftoverMapIncompletePostCount(coverage({ incomplete_post_count: Number.NaN }))).toBeNull();
  });

  it("does not invent leftover-map incomplete posts from scored minus used or from plotted marker count", () => {
    expect(
      leftoverMapIncompletePostCount(
        coverage({
          map_post_count: 2,
          scored_post_count: 3,
          incomplete_post_count: 2,
        }),
      ),
    ).toBeNull();
    expect(leftoverMapIncompletePostCount(coverage({ incomplete_post_count: 1 }))).not.toEqual({
      dropped: 2,
    });
  });

  it("keeps the pair-list incomplete post label distinct from the graphic incomplete post label", () => {
    expect(LEFTOVER_MAP_LIST_INCOMPLETE_POST_LABEL).toBe("Leftover map incomplete posts");
    expect(LEFTOVER_MAP_PLOT_INCOMPLETE_POST_LABEL).toBe("Leftover-map graphic incomplete posts");
    expect(LEFTOVER_MAP_LIST_INCOMPLETE_POST_LABEL).not.toBe(LEFTOVER_MAP_PLOT_INCOMPLETE_POST_LABEL);
  });

  it("keeps the grouping comparison incomplete post label distinct from the pair-list and graphic incomplete post labels", () => {
    expect(LEFTOVER_MAP_COMPARE_INCOMPLETE_POST_LABEL).toBe("Leftover map comparison incomplete posts");
    expect(LEFTOVER_MAP_COMPARE_INCOMPLETE_POST_LABEL).not.toBe(LEFTOVER_MAP_LIST_INCOMPLETE_POST_LABEL);
    expect(LEFTOVER_MAP_COMPARE_INCOMPLETE_POST_LABEL).not.toBe(LEFTOVER_MAP_PLOT_INCOMPLETE_POST_LABEL);
  });
});

describe("leftoverMapIncompleteItemCount", () => {
  it("names persisted leftover-map incomplete item coverage without inventing a leftover score", () => {
    expect(leftoverMapIncompleteItemCount(coverage())).toEqual({ dropped: 0 });
    expect(
      leftoverMapIncompleteItemCount(
        coverage({ map_item_count: 0, scored_item_count: 2, incomplete_item_count: 2 }),
      ),
    ).toEqual({ dropped: 2 });
    expect(
      leftoverMapIncompleteItemCount(
        coverage({ map_item_count: 1, scored_item_count: 2, incomplete_item_count: 1 }),
      ),
    ).toEqual({ dropped: 1 });
  });

  it("omits incomplete item coverage when the dropped count is missing or not a usable integer", () => {
    expect(leftoverMapIncompleteItemCount(null)).toBeNull();
    expect(leftoverMapIncompleteItemCount(undefined)).toBeNull();
    expect(leftoverMapIncompleteItemCount(coverage({ incomplete_item_count: -1 }))).toBeNull();
    expect(leftoverMapIncompleteItemCount(coverage({ incomplete_item_count: 1.5 }))).toBeNull();
    expect(leftoverMapIncompleteItemCount(coverage({ incomplete_item_count: Number.NaN }))).toBeNull();
  });

  it("does not invent leftover-map incomplete items from scored minus used or from plotted criterion marker count", () => {
    expect(
      leftoverMapIncompleteItemCount(
        coverage({
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_item_count: 1,
        }),
      ),
    ).toBeNull();
    expect(leftoverMapIncompleteItemCount(coverage({ incomplete_item_count: 0 }))).not.toEqual({
      dropped: 1,
    });
  });

  it("keeps the pair-list incomplete item label distinct from the graphic incomplete item label", () => {
    expect(LEFTOVER_MAP_LIST_INCOMPLETE_ITEM_LABEL).toBe("Leftover map incomplete items");
    expect(LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM_LABEL).toBe("Leftover-map graphic incomplete items");
    expect(LEFTOVER_MAP_LIST_INCOMPLETE_ITEM_LABEL).not.toBe(LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM_LABEL);
  });

  it("keeps the grouping comparison incomplete item label distinct from the pair-list and graphic incomplete item labels", () => {
    expect(LEFTOVER_MAP_COMPARE_INCOMPLETE_ITEM_LABEL).toBe("Leftover map comparison incomplete items");
    expect(LEFTOVER_MAP_COMPARE_INCOMPLETE_ITEM_LABEL).not.toBe(LEFTOVER_MAP_LIST_INCOMPLETE_ITEM_LABEL);
    expect(LEFTOVER_MAP_COMPARE_INCOMPLETE_ITEM_LABEL).not.toBe(LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM_LABEL);
  });
});
