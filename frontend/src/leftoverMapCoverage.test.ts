import { describe, expect, it } from "vitest";
import type { LeftoverMapCoverage } from "./api";
import {
  leftoverMapCoverageCounts,
  leftoverMapIncompleteItemCount,
  leftoverMapIncompletePostCount,
  leftoverMapItemCoverageCounts,
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
});
