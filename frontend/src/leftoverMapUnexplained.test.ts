import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapUnexplained,
  formatSignedLeftoverValue,
  LEFTOVER_MAP_COMPARE_UNEXPLAINED_LABEL,
} from "./leftoverMapUnexplained";

describe("formatLeftoverMapUnexplained", () => {
  it("names unexplained leftover without inventing a leftover score", () => {
    expect(formatLeftoverMapUnexplained(0.05)).toBe("U +0.05");
    expect(formatLeftoverMapUnexplained(-0.25)).toBe("U \u22120.25");
    expect(formatLeftoverMapUnexplained(0)).toBe("U 0.00");
    expect(formatSignedLeftoverValue(0.05)).toBe("+0.05");
    expect(formatSignedLeftoverValue(-0.25)).toBe("\u22120.25");
  });

  it("omits the badge when unexplained leftover is missing or non-finite", () => {
    expect(formatLeftoverMapUnexplained(null)).toBeNull();
    expect(formatLeftoverMapUnexplained(undefined)).toBeNull();
    expect(formatLeftoverMapUnexplained(Number.NaN)).toBeNull();
    expect(formatLeftoverMapUnexplained(Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("keeps the grouping comparison unexplained leftover label distinct from the graphic unexplained leftover label", () => {
    expect(LEFTOVER_MAP_COMPARE_UNEXPLAINED_LABEL).toBe(
      "Leftover map comparison unexplained leftover",
    );
    expect(LEFTOVER_MAP_COMPARE_UNEXPLAINED_LABEL).not.toBe(
      "leftover-map unexplained leftover {label}",
    );
    expect(LEFTOVER_MAP_COMPARE_UNEXPLAINED_LABEL).not.toBe(
      "Leftover map comparison unexplained leftover share",
    );
  });
});
