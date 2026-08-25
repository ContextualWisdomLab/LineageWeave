import { describe, expect, it } from "vitest";
import { formatLeftoverMapCrossShare } from "./leftoverMapCrossShare";

describe("formatLeftoverMapCrossShare", () => {
  it("names leftover-map cross share without inventing a leftover score", () => {
    expect(formatLeftoverMapCrossShare(0.12)).toBe("2R\u0302U/R\u00b2 0.12");
    expect(formatLeftoverMapCrossShare(0)).toBe("2R\u0302U/R\u00b2 0.00");
    expect(formatLeftoverMapCrossShare(-0.24)).toBe("2R\u0302U/R\u00b2 -0.24");
  });

  it("omits the badge when leftover-map cross share is missing or non-finite", () => {
    expect(formatLeftoverMapCrossShare(null)).toBeNull();
    expect(formatLeftoverMapCrossShare(undefined)).toBeNull();
    expect(formatLeftoverMapCrossShare(Number.NaN)).toBeNull();
    expect(formatLeftoverMapCrossShare(Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapCrossShare(Number.NEGATIVE_INFINITY)).toBeNull();
  });
});
