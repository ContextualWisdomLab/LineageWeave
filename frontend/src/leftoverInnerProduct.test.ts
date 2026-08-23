import { describe, expect, it } from "vitest";
import { formatLeftoverInnerProduct, formatSignedLeftoverValue } from "./leftoverInnerProduct";

describe("formatLeftoverInnerProduct", () => {
  it("names leftover-map inner product without inventing a leftover score", () => {
    expect(formatLeftoverInnerProduct(0.4)).toBe("ξ·ζ +0.40");
    expect(formatLeftoverInnerProduct(-1.1)).toBe("ξ·ζ \u22121.10");
    expect(formatLeftoverInnerProduct(0)).toBe("ξ·ζ 0.00");
    expect(formatSignedLeftoverValue(0.4)).toBe("+0.40");
    expect(formatSignedLeftoverValue(-1.1)).toBe("\u22121.10");
  });

  it("omits the badge when the inner product is missing or non-finite", () => {
    expect(formatLeftoverInnerProduct(null)).toBeNull();
    expect(formatLeftoverInnerProduct(undefined)).toBeNull();
    expect(formatLeftoverInnerProduct(Number.NaN)).toBeNull();
    expect(formatLeftoverInnerProduct(Number.POSITIVE_INFINITY)).toBeNull();
  });
});
