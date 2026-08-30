import { describe, expect, it } from "vitest";
import { formatLeftoverMapObserved, formatLeftoverObservedExpected } from "./leftoverObservedExpected";

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

describe("formatLeftoverMapObserved", () => {
  it("names leftover observed without inventing a leftover score", () => {
    expect(formatLeftoverMapObserved(2.4)).toBe("Y 2.40");
    expect(formatLeftoverMapObserved(0.9)).toBe("Y 0.90");
    expect(formatLeftoverMapObserved(0)).toBe("Y 0.00");
    expect(formatLeftoverMapObserved(-1.1)).toBe("Y -1.10");
  });

  it("omits the badge when leftover observed is missing or non-finite", () => {
    expect(formatLeftoverMapObserved(null)).toBeNull();
    expect(formatLeftoverMapObserved(undefined)).toBeNull();
    expect(formatLeftoverMapObserved(Number.NaN)).toBeNull();
    expect(formatLeftoverMapObserved(Number.POSITIVE_INFINITY)).toBeNull();
  });
});
