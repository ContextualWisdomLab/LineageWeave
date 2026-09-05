import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapCoordinatePair,
  formatLeftoverMapCoordinates,
  LEFTOVER_MAP_COMPARE_COORDINATES_LABEL,
} from "./leftoverMapCoordinates";

describe("formatLeftoverMapCoordinates", () => {
  it("names leftover-map coordinates without inventing a leftover score", () => {
    expect(formatLeftoverMapCoordinates(0.5, 0.1, 0.5, -0.02)).toBe(
      "\u03BE (+0.50, +0.10) \u03B6 (+0.50, \u22120.02)",
    );
    expect(formatLeftoverMapCoordinates(0, 0, 0, 0)).toBe(
      "\u03BE (0.00, 0.00) \u03B6 (0.00, 0.00)",
    );
    expect(formatLeftoverMapCoordinates(-1.25, 2, 0.5, 0)).toBe(
      "\u03BE (\u22121.25, +2.00) \u03B6 (+0.50, 0.00)",
    );
  });

  it("omits the badge when any leftover-map coordinate is missing or non-finite", () => {
    expect(formatLeftoverMapCoordinates(null, 0, 0, 0)).toBeNull();
    expect(formatLeftoverMapCoordinates(0, undefined, 0, 0)).toBeNull();
    expect(formatLeftoverMapCoordinates(0, 0, Number.NaN, 0)).toBeNull();
    expect(formatLeftoverMapCoordinates(0, 0, 0, Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapCoordinates(0, Number.NEGATIVE_INFINITY, 0, 0)).toBeNull();
  });

  it("keeps the grouping comparison coordinates label distinct from the graphic tick label", () => {
    expect(LEFTOVER_MAP_COMPARE_COORDINATES_LABEL).toBe("Leftover map comparison coordinates");
    expect(LEFTOVER_MAP_COMPARE_COORDINATES_LABEL).not.toBe("leftover-map axis {axis} tick {value}");
  });
});

describe("formatLeftoverMapCoordinatePair", () => {
  it("names one leftover-map position without inventing a leftover score", () => {
    expect(formatLeftoverMapCoordinatePair(0.5, -0.02)).toBe("(+0.50, \u22120.02)");
    expect(formatLeftoverMapCoordinatePair(0, 0)).toBe("(0.00, 0.00)");
  });

  it("omits a pair when either leftover-map axis is missing or non-finite", () => {
    expect(formatLeftoverMapCoordinatePair(null, 0)).toBeNull();
    expect(formatLeftoverMapCoordinatePair(0, Number.NaN)).toBeNull();
  });
});
