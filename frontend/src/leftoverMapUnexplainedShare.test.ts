import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapUnexplainedShare,
  LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL,
} from "./leftoverMapUnexplainedShare";

describe("formatLeftoverMapUnexplainedShare", () => {
  it("names leftover-map unexplained leftover share without inventing a leftover score", () => {
    expect(formatLeftoverMapUnexplainedShare(0.02)).toBe("U\u00b2/R\u00b2 0.02");
    expect(formatLeftoverMapUnexplainedShare(0)).toBe("U\u00b2/R\u00b2 0.00");
    expect(formatLeftoverMapUnexplainedShare(1.25)).toBe("U\u00b2/R\u00b2 1.25");
  });

  it("omits the badge when leftover-map unexplained leftover share is missing or non-finite", () => {
    expect(formatLeftoverMapUnexplainedShare(null)).toBeNull();
    expect(formatLeftoverMapUnexplainedShare(undefined)).toBeNull();
    expect(formatLeftoverMapUnexplainedShare(Number.NaN)).toBeNull();
    expect(formatLeftoverMapUnexplainedShare(Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapUnexplainedShare(Number.NEGATIVE_INFINITY)).toBeNull();
  });

  it("keeps the grouping comparison unexplained leftover share label distinct from the graphic unexplained leftover share label", () => {
    expect(LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL).toBe(
      "Leftover map comparison unexplained leftover share",
    );
    expect(LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL).not.toBe(
      "leftover-map unexplained leftover share {label}",
    );
  });
});
