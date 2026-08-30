import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapReconstruction,
  LEFTOVER_MAP_COMPARE_RECONSTRUCTION_LABEL,
} from "./leftoverMapReconstruction";

describe("formatLeftoverMapReconstruction", () => {
  it("names leftover-map reconstruction without inventing a leftover score", () => {
    expect(formatLeftoverMapReconstruction(0.35)).toBe("R\u0302 +0.35");
    expect(formatLeftoverMapReconstruction(-0.85)).toBe("R\u0302 \u22120.85");
    expect(formatLeftoverMapReconstruction(0)).toBe("R\u0302 0.00");
  });

  it("omits the badge when reconstruction is missing or non-finite", () => {
    expect(formatLeftoverMapReconstruction(null)).toBeNull();
    expect(formatLeftoverMapReconstruction(undefined)).toBeNull();
    expect(formatLeftoverMapReconstruction(Number.NaN)).toBeNull();
    expect(formatLeftoverMapReconstruction(Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("keeps the grouping comparison reconstruction label distinct from the graphic reconstruction label", () => {
    expect(LEFTOVER_MAP_COMPARE_RECONSTRUCTION_LABEL).toBe("Leftover map comparison reconstruction");
    expect(LEFTOVER_MAP_COMPARE_RECONSTRUCTION_LABEL).not.toBe("leftover-map reconstruction {label}");
  });
});
