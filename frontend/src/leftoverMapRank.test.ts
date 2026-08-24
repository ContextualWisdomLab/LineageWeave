import { describe, expect, it } from "vitest";
import { formatLeftoverMapRank } from "./leftoverMapRank";

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
