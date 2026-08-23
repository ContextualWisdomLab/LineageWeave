import { describe, expect, it } from "vitest";
import { formatLeftoverMapRank, leftoverMapRankNextAction } from "./leftoverMapRank";

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
});

describe("leftoverMapRankNextAction", () => {
  it("tells the buyer to open the post after reading leftover-map rank", () => {
    expect(leftoverMapRankNextAction(0)).toBe(
      "Leftover map has no leftover structure after IRT main effects. Open this post.",
    );
    expect(leftoverMapRankNextAction(1)).toBe(
      "Leftover map rank 1 after IRT main effects. Open this post.",
    );
  });

  it("omits the next-action rewrite when rank is missing", () => {
    expect(leftoverMapRankNextAction(null)).toBeNull();
    expect(leftoverMapRankNextAction(-1)).toBeNull();
  });
});
