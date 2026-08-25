import { describe, expect, it } from "vitest";
import { formatLeftoverMapReconstruction } from "./leftoverMapReconstruction";

describe("formatLeftoverMapReconstruction", () => {
  it("names leftover-map reconstruction without inventing a leftover score", () => {
    expect(formatLeftoverMapReconstruction(0.35)).toBe("R\u0302 +0.35");
    expect(formatLeftoverMapReconstruction(-0.85)).toBe("R\u0302 \u22120.85");
    expect(formatLeftoverMapReconstruction(0)).toBe("R\u0302 0.00");
  });

  it("omits the badge when reconstruction is missing or non-finite", () => {
    expect(formatLeftoverMapReconstruction(null)).toBeNull();
    expect(formatLeftoverMapReconstruction(undefined)).toBeNull();
    expect(formatLeftoverMapReconstruction(Number.NaN)).toBeNull();
    expect(formatLeftoverMapReconstruction(Number.POSITIVE_INFINITY)).toBeNull();
  });
});
