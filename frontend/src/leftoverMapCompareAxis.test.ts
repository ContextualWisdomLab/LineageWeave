import { describe, expect, it } from "vitest";
import {
  leftoverMapCompareAxisShare,
  LEFTOVER_MAP_COMPARE_AXIS_SHARE,
  LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL,
  LEFTOVER_MAP_LIST_AXIS_SHARE,
  LEFTOVER_MAP_PLOT_AXIS_SHARE,
} from "./leftoverMapCompareAxis";

describe("leftoverMapCompareAxisShare", () => {
  it("names persisted leftover-map axis share without inventing a leftover score", () => {
    expect(
      leftoverMapCompareAxisShare({ axis_index: 1, leftover_share: 0.82 }),
    ).toEqual({ axis: 1, share: "82" });
    expect(
      leftoverMapCompareAxisShare({ axis_index: 2, leftover_share: 0.18 }),
    ).toEqual({ axis: 2, share: "18" });
  });

  it("names a rank-0 zero leftover-map axis share", () => {
    expect(leftoverMapCompareAxisShare({ axis_index: 1, leftover_share: 0 })).toEqual({
      axis: 1,
      share: "0",
    });
  });

  it("names a finite negative leftover-map axis share without clamping", () => {
    expect(leftoverMapCompareAxisShare({ axis_index: 1, leftover_share: -0.1 })).toEqual({
      axis: 1,
      share: "-10",
    });
  });

  it("omits leftover-map axis share that is missing or non-finite", () => {
    expect(leftoverMapCompareAxisShare(null)).toBeNull();
    expect(leftoverMapCompareAxisShare(undefined)).toBeNull();
    expect(
      leftoverMapCompareAxisShare({ axis_index: 1, leftover_share: Number.NaN }),
    ).toBeNull();
    expect(
      leftoverMapCompareAxisShare({ axis_index: 1, leftover_share: Number.POSITIVE_INFINITY }),
    ).toBeNull();
  });

  it("does not invent leftover-map axis share from leftover-map singular value", () => {
    expect(
      leftoverMapCompareAxisShare({
        axis_index: 1,
        leftover_share: Number.NaN,
      }),
    ).toBeNull();
    expect(leftoverMapCompareAxisShare({ axis_index: 1, leftover_share: 0.82 })).not.toEqual({
      axis: 1,
      share: "1.84",
    });
  });

  it("keeps the grouping comparison leftover-map axis share label distinct from leftover-axis badges and graphic axes", () => {
    expect(LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL).toBe("Leftover map comparison axis share");
    expect(LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL).not.toBe("Leftover-map axis share");
    expect(LEFTOVER_MAP_COMPARE_AXIS_SHARE).toBe("leftover map comparison axis {axis} {share}%");
    expect(LEFTOVER_MAP_COMPARE_AXIS_SHARE).not.toBe(LEFTOVER_MAP_LIST_AXIS_SHARE);
    expect(LEFTOVER_MAP_COMPARE_AXIS_SHARE).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SHARE);
  });
});
