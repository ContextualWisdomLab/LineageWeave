import { describe, expect, it } from "vitest";
import { formatLeftoverObservedExpected } from "./leftoverObservedExpected";

describe("formatLeftoverObservedExpected", () => {
  it("names observed Y and expected E without inventing a leftover score", () => {
    expect(formatLeftoverObservedExpected(2.4, 2.0)).toBe("Y 2.40 · E 2.00");
    expect(formatLeftoverObservedExpected(0.9, 2.0)).toBe("Y 0.90 · E 2.00");
    expect(formatLeftoverObservedExpected(0, 0)).toBe("Y 0.00 · E 0.00");
  });

  it("omits the badge when Y or E is missing or non-finite", () => {
    expect(formatLeftoverObservedExpected(null, 2.0)).toBeNull();
    expect(formatLeftoverObservedExpected(2.4, undefined)).toBeNull();
    expect(formatLeftoverObservedExpected(Number.NaN, 2.0)).toBeNull();
    expect(formatLeftoverObservedExpected(2.4, Number.POSITIVE_INFINITY)).toBeNull();
  });
});
