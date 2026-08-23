import { describe, expect, it } from "vitest";
import { formatLeftoverResidual } from "./leftoverResidual";

describe("formatLeftoverResidual", () => {
  it("keeps a signed residual without inventing a leftover score", () => {
    expect(formatLeftoverResidual(0.4)).toBe("+0.40");
    expect(formatLeftoverResidual(-1.1)).toBe("\u22121.10");
    expect(formatLeftoverResidual(0)).toBe("0.00");
    expect(formatLeftoverResidual(Number.NaN)).toBe("—");
  });
});
