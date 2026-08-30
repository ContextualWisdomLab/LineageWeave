import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapResidual,
  formatLeftoverResidual,
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL,
  LEFTOVER_MAP_COMPARE_RESIDUAL_LABEL,
} from "./leftoverResidual";

describe("formatLeftoverResidual", () => {
  it("keeps a signed residual without inventing a leftover score", () => {
    expect(formatLeftoverResidual(0.4)).toBe("+0.40");
    expect(formatLeftoverResidual(-1.1)).toBe("\u22121.10");
    expect(formatLeftoverResidual(0)).toBe("0.00");
    expect(formatLeftoverResidual(Number.NaN)).toBe("—");
  });
});

describe("formatLeftoverMapResidual", () => {
  it("names leftover residual without inventing a leftover score", () => {
    expect(formatLeftoverMapResidual(0.4)).toBe("R +0.40");
    expect(formatLeftoverMapResidual(-1.1)).toBe("R \u22121.10");
    expect(formatLeftoverMapResidual(0)).toBe("R 0.00");
  });

  it("omits the badge when leftover residual is missing or non-finite", () => {
    expect(formatLeftoverMapResidual(null)).toBeNull();
    expect(formatLeftoverMapResidual(undefined)).toBeNull();
    expect(formatLeftoverMapResidual(Number.NaN)).toBeNull();
    expect(formatLeftoverMapResidual(Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("keeps the grouping comparison residual label distinct from the graphic residual label", () => {
    expect(LEFTOVER_MAP_COMPARE_RESIDUAL_LABEL).toBe("Leftover map comparison residual");
    expect(LEFTOVER_MAP_COMPARE_RESIDUAL_LABEL).not.toBe("leftover residual {label}");
  });

  it("keeps the grouping comparison graphic residual label distinct from the graphic and strip labels", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL).toBe(
      "leftover map comparison graphic residual {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL).not.toBe("leftover residual {label}");
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL).not.toBe(
      LEFTOVER_MAP_COMPARE_RESIDUAL_LABEL,
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RESIDUAL).not.toBe(
      "leftover map comparison graphic unexplained leftover {label}",
    );
  });
});
