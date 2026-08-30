import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapExplainedShare,
  LEFTOVER_MAP_COMPARE_EXPLAINED_SHARE_LABEL,
} from "./leftoverMapExplainedShare";

describe("formatLeftoverMapExplainedShare", () => {
  it("names leftover-map explained leftover share without inventing a leftover score", () => {
    expect(formatLeftoverMapExplainedShare(0.76)).toBe("R\u0302\u00b2/R\u00b2 0.76");
    expect(formatLeftoverMapExplainedShare(0)).toBe("R\u0302\u00b2/R\u00b2 0.00");
    expect(formatLeftoverMapExplainedShare(1.25)).toBe("R\u0302\u00b2/R\u00b2 1.25");
  });

  it("omits the badge when leftover-map explained leftover share is missing or non-finite", () => {
    expect(formatLeftoverMapExplainedShare(null)).toBeNull();
    expect(formatLeftoverMapExplainedShare(undefined)).toBeNull();
    expect(formatLeftoverMapExplainedShare(Number.NaN)).toBeNull();
    expect(formatLeftoverMapExplainedShare(Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapExplainedShare(Number.NEGATIVE_INFINITY)).toBeNull();
  });

  it("keeps the grouping comparison explained leftover share label distinct from the graphic explained leftover share label", () => {
    expect(LEFTOVER_MAP_COMPARE_EXPLAINED_SHARE_LABEL).toBe(
      "Leftover map comparison explained leftover share",
    );
    expect(LEFTOVER_MAP_COMPARE_EXPLAINED_SHARE_LABEL).not.toBe(
      "leftover-map explained leftover share {label}",
    );
  });
});
