import { describe, expect, it } from "vitest";
import { formatLeftoverMapResidual, formatLeftoverResidual } from "./leftoverResidual";

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
});
