import { describe, expect, it } from "vitest";
import { formatLeftoverMapExplainedShare } from "./leftoverMapExplainedShare";

describe("formatLeftoverMapExplainedShare", () => {
  it("names explained leftover share without inventing a leftover score", () => {
    expect(formatLeftoverMapExplainedShare(0.88)).toBe("R\u0302c\u00b2/R\u0303\u00b2 0.88");
    expect(formatLeftoverMapExplainedShare(0)).toBe("R\u0302c\u00b2/R\u0303\u00b2 0.00");
    expect(formatLeftoverMapExplainedShare(1)).toBe("R\u0302c\u00b2/R\u0303\u00b2 1.00");
  });

  it("omits the badge when explained leftover share is missing, negative, or non-finite", () => {
    expect(formatLeftoverMapExplainedShare(null)).toBeNull();
    expect(formatLeftoverMapExplainedShare(undefined)).toBeNull();
    expect(formatLeftoverMapExplainedShare(Number.NaN)).toBeNull();
    expect(formatLeftoverMapExplainedShare(Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapExplainedShare(-0.01)).toBeNull();
  });
});
