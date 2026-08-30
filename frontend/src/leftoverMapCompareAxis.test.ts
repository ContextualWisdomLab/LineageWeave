import { describe, expect, it } from "vitest";
import {
  leftoverMapCompareAxisShare,
  leftoverMapCompareAxisSingular,
  LEFTOVER_MAP_COMPARE_AXIS_SHARE,
  LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL,
  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_LABEL,
  LEFTOVER_MAP_LIST_AXIS_SHARE,
  LEFTOVER_MAP_LIST_AXIS_SINGULAR,
  LEFTOVER_MAP_PLOT_AXIS_SHARE,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR,
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

describe("leftoverMapCompareAxisSingular", () => {
  it("names persisted leftover-map singular values without inventing a leftover score", () => {
    expect(
      leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: 1.84 }),
    ).toEqual({ axis: 1, value: "1.84" });
    expect(
      leftoverMapCompareAxisSingular({ axis_index: 2, leftover_singular_value: 0.86 }),
    ).toEqual({ axis: 2, value: "0.86" });
  });

  it("names a rank-0 zero leftover-map singular value", () => {
    expect(
      leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: 0 }),
    ).toEqual({ axis: 1, value: "0.00" });
  });

  it("omits leftover-map singular values that are missing, non-finite, or negative", () => {
    expect(leftoverMapCompareAxisSingular(null)).toBeNull();
    expect(leftoverMapCompareAxisSingular(undefined)).toBeNull();
    expect(leftoverMapCompareAxisSingular({ axis_index: 1 })).toBeNull();
    expect(
      leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: Number.NaN }),
    ).toBeNull();
    expect(
      leftoverMapCompareAxisSingular({
        axis_index: 1,
        leftover_singular_value: Number.POSITIVE_INFINITY,
      }),
    ).toBeNull();
    expect(
      leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: -0.01 }),
    ).toBeNull();
  });

  it("does not invent leftover-map singular value from leftover-map axis share", () => {
    expect(
      leftoverMapCompareAxisSingular({
        axis_index: 1,
        leftover_singular_value: Number.NaN,
      }),
    ).toBeNull();
    expect(
      leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: 1.84 }),
    ).not.toEqual({ axis: 1, value: "82" });
  });

  it("keeps the grouping comparison leftover-map singular caption distinct from leftover-axis badges and graphic axes", () => {
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_LABEL).toBe(
      "Leftover map comparison axis singular",
    );
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_LABEL).not.toBe(
      LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL,
    );
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR).toBe(
      "leftover map comparison axis {axis} σ {value}",
    );
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR).not.toBe(LEFTOVER_MAP_LIST_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR);
  });
});
