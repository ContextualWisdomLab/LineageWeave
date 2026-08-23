import { describe, expect, it } from "vitest";
import { formatLeftoverMapUnexplainedShare } from "./leftoverMapUnexplainedShare";

describe("formatLeftoverMapUnexplainedShare", () => {
  it("names unexplained leftover share without inventing a leftover score", () => {
    expect(formatLeftoverMapUnexplainedShare(0.12)).toBe("U\u00b2/R\u0303\u00b2 0.12");
    expect(formatLeftoverMapUnexplainedShare(0)).toBe("U\u00b2/R\u0303\u00b2 0.00");
    expect(formatLeftoverMapUnexplainedShare(1)).toBe("U\u00b2/R\u0303\u00b2 1.00");
  });

  it("omits the badge when unexplained leftover share is missing, negative, or non-finite", () => {
    expect(formatLeftoverMapUnexplainedShare(null)).toBeNull();
    expect(formatLeftoverMapUnexplainedShare(undefined)).toBeNull();
    expect(formatLeftoverMapUnexplainedShare(Number.NaN)).toBeNull();
    expect(formatLeftoverMapUnexplainedShare(Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapUnexplainedShare(-0.01)).toBeNull();
  });
});
