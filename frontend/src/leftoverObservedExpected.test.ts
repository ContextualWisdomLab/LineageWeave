import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapExpected,
  formatLeftoverMapObserved,
  formatLeftoverObservedExpected,
  LEFTOVER_MAP_COMPARE_OBSERVED_LABEL,
  LEFTOVER_MAP_COMPARE_EXPECTED_LABEL,
} from "./leftoverObservedExpected";

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

  it("keeps the grouping comparison observed label distinct from the graphic observed label", () => {
    expect(LEFTOVER_MAP_COMPARE_OBSERVED_LABEL).toBe("Leftover map comparison observed");
    expect(LEFTOVER_MAP_COMPARE_OBSERVED_LABEL).not.toBe("leftover observed {label}");
  });
});

describe("formatLeftoverMapExpected", () => {
  it("names leftover expected without inventing a leftover score", () => {
    expect(formatLeftoverMapExpected(2.0)).toBe("E 2.00");
    expect(formatLeftoverMapExpected(0.9)).toBe("E 0.90");
    expect(formatLeftoverMapExpected(0)).toBe("E 0.00");
    expect(formatLeftoverMapExpected(-1.1)).toBe("E -1.10");
  });

  it("omits the badge when leftover expected is missing or non-finite", () => {
    expect(formatLeftoverMapExpected(null)).toBeNull();
    expect(formatLeftoverMapExpected(undefined)).toBeNull();
    expect(formatLeftoverMapExpected(Number.NaN)).toBeNull();
    expect(formatLeftoverMapExpected(Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("keeps the grouping comparison expected label distinct from the graphic expected label", () => {
    expect(LEFTOVER_MAP_COMPARE_EXPECTED_LABEL).toBe("Leftover map comparison expected");
    expect(LEFTOVER_MAP_COMPARE_EXPECTED_LABEL).not.toBe("leftover expected {label}");
  });
});
