import { describe, expect, it } from "vitest";
import { formatLeftoverMapExplainedShare } from "./leftoverMapExplainedShare";

describe("formatLeftoverMapExplainedShare", () => {
  it("names leftover-map explained share without inventing a leftover score", () => {
    expect(formatLeftoverMapExplainedShare(0.76)).toBe("R\u0302\u00b2/R\u00b2 0.76");
    expect(formatLeftoverMapExplainedShare(0)).toBe("R\u0302\u00b2/R\u00b2 0.00");
    expect(formatLeftoverMapExplainedShare(1.25)).toBe("R\u0302\u00b2/R\u00b2 1.25");
  });

  it("omits the badge when leftover-map explained share is missing or non-finite", () => {
    expect(formatLeftoverMapExplainedShare(null)).toBeNull();
    expect(formatLeftoverMapExplainedShare(undefined)).toBeNull();
    expect(formatLeftoverMapExplainedShare(Number.NaN)).toBeNull();
    expect(formatLeftoverMapExplainedShare(Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapExplainedShare(Number.NEGATIVE_INFINITY)).toBeNull();
  });
});
