import { describe, expect, it } from "vitest";
import { formatLeftoverMapCosine, formatSignedLeftoverValue } from "./leftoverMapCosine";

describe("formatLeftoverMapCosine", () => {
  it("names leftover-map cosine without inventing a leftover score", () => {
    expect(formatLeftoverMapCosine(0.95)).toBe("cos +0.95");
    expect(formatLeftoverMapCosine(-1)).toBe("cos −1.00");
    expect(formatLeftoverMapCosine(0)).toBe("cos 0.00");
    expect(formatSignedLeftoverValue(0.95)).toBe("+0.95");
    expect(formatSignedLeftoverValue(-1)).toBe("−1.00");
  });

  it("omits the badge when cosine is missing or non-finite", () => {
    expect(formatLeftoverMapCosine(null)).toBeNull();
    expect(formatLeftoverMapCosine(undefined)).toBeNull();
    expect(formatLeftoverMapCosine(Number.NaN)).toBeNull();
    expect(formatLeftoverMapCosine(Number.POSITIVE_INFINITY)).toBeNull();
  });
});
