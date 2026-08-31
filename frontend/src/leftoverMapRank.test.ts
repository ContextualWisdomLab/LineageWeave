import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapRank,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK,
  LEFTOVER_MAP_COMPARE_RANK_LABEL,
} from "./leftoverMapRank";

describe("formatLeftoverMapRank", () => {
  it("names leftover-map rank without inventing leftover structure", () => {
    expect(formatLeftoverMapRank(0)).toBe("rank 0");
    expect(formatLeftoverMapRank(1)).toBe("rank 1");
    expect(formatLeftoverMapRank(2)).toBe("rank 2");
  });

  it("omits the badge when rank is missing or not a non-negative integer", () => {
    expect(formatLeftoverMapRank(null)).toBeNull();
    expect(formatLeftoverMapRank(undefined)).toBeNull();
    expect(formatLeftoverMapRank(-1)).toBeNull();
    expect(formatLeftoverMapRank(1.5)).toBeNull();
    expect(formatLeftoverMapRank(Number.NaN)).toBeNull();
  });

  it("keeps the grouping comparison rank label distinct from the graphic rank label", () => {
    expect(LEFTOVER_MAP_COMPARE_RANK_LABEL).toBe("Leftover map comparison rank");
    expect(LEFTOVER_MAP_COMPARE_RANK_LABEL).not.toBe("leftover-map rank {label}");
  });

  it("keeps the grouping comparison graphic leftover-map rank label distinct from the graphic and strip labels", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK).toBe(
      "leftover map comparison graphic leftover-map rank {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK).not.toBe("leftover-map rank {label}");
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK).not.toBe(
      LEFTOVER_MAP_COMPARE_RANK_LABEL,
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK).not.toBe(
      "leftover map comparison graphic leftover expected {label}",
    );
  });
});
