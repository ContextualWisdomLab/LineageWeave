import { describe, expect, it } from "vitest";
import { formatLeftoverMapReconstruction } from "./leftoverMapReconstruction";

describe("formatLeftoverMapReconstruction", () => {
  it("names leftover-map reconstruction without inventing a leftover score", () => {
    expect(formatLeftoverMapReconstruction(0.4)).toBe("R̂ +0.40");
    expect(formatLeftoverMapReconstruction(-1.1)).toBe("R̂ −1.10");
    expect(formatLeftoverMapReconstruction(0)).toBe("R̂ 0.00");
  });

  it("omits the badge when reconstruction is missing or non-finite", () => {
    expect(formatLeftoverMapReconstruction(null)).toBeNull();
    expect(formatLeftoverMapReconstruction(undefined)).toBeNull();
    expect(formatLeftoverMapReconstruction(Number.NaN)).toBeNull();
    expect(formatLeftoverMapReconstruction(Number.POSITIVE_INFINITY)).toBeNull();
  });
});
