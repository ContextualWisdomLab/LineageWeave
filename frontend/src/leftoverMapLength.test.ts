import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapItemLength,
  formatLeftoverMapLength,
  formatLeftoverMapPersonLength,
} from "./leftoverMapLength";

describe("formatLeftoverMapLength", () => {
  it("names leftover-map length without inventing a leftover score", () => {
    expect(formatLeftoverMapPersonLength(0)).toBe("‖ξ‖ 0.00");
    expect(formatLeftoverMapItemLength(1.25)).toBe("‖ζ‖ 1.25");
    expect(formatLeftoverMapLength(0.4)).toBe("0.40");
    expect(formatLeftoverMapPersonLength(0.4)).toBe("‖ξ‖ 0.40");
    expect(formatLeftoverMapItemLength(0.9)).toBe("‖ζ‖ 0.90");
  });

  it("omits the badge when length is missing, negative, or non-finite", () => {
    expect(formatLeftoverMapPersonLength(null)).toBeNull();
    expect(formatLeftoverMapItemLength(undefined)).toBeNull();
    expect(formatLeftoverMapLength(Number.NaN)).toBeNull();
    expect(formatLeftoverMapLength(Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapLength(-0.01)).toBeNull();
  });
});
