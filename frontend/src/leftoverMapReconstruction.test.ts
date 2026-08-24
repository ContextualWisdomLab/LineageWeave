import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapReconstruction,
  formatSignedLeftoverValue,
} from "./leftoverMapReconstruction";

describe("formatLeftoverMapReconstruction", () => {
  it("names two-axis leftover-map reconstruction without inventing a leftover score", () => {
    expect(formatLeftoverMapReconstruction(0.4)).toBe("R\u0302 +0.40");
    expect(formatLeftoverMapReconstruction(-1.1)).toBe("R\u0302 \u22121.10");
    expect(formatLeftoverMapReconstruction(0)).toBe("R\u0302 0.00");
    expect(formatSignedLeftoverValue(0.4)).toBe("+0.40");
    expect(formatSignedLeftoverValue(-1.1)).toBe("\u22121.10");
  });

  it("omits the badge when reconstruction is missing or non-finite", () => {
    expect(formatLeftoverMapReconstruction(null)).toBeNull();
    expect(formatLeftoverMapReconstruction(undefined)).toBeNull();
    expect(formatLeftoverMapReconstruction(Number.NaN)).toBeNull();
    expect(formatLeftoverMapReconstruction(Number.POSITIVE_INFINITY)).toBeNull();
  });
});
