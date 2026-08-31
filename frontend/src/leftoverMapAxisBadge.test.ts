import { describe, expect, it } from "vitest";
import {
  leftoverMapAxisBadgeShare,
  leftoverMapAxisBadgeSingular,
  LEFTOVER_MAP_AXIS_BADGE_SHARE,
  LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
} from "./leftoverMapAxisBadge";
import {
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE,
} from "./leftoverMapPlotAxisSingular";

describe("leftoverMapAxisBadgeShare", () => {
  it("formats leftover-axis share percent without inventing a leftover score", () => {
    expect(leftoverMapAxisBadgeShare(0.82)).toBe("82");
    expect(leftoverMapAxisBadgeShare(0.18)).toBe("18");
    expect(leftoverMapAxisBadgeShare(0)).toBe("0");
  });
});

describe("leftoverMapAxisBadgeSingular", () => {
  it("reads persisted leftover-map singular values without inventing a leftover score", () => {
    expect(
      leftoverMapAxisBadgeSingular({ axis_index: 1, leftover_singular_value: 1.84 }),
    ).toBe("1.84");
    expect(
      leftoverMapAxisBadgeSingular({ axis_index: 2, leftover_singular_value: 0.86 }),
    ).toBe("0.86");
  });

  it("names a rank-0 zero leftover-map singular value", () => {
    expect(leftoverMapAxisBadgeSingular({ axis_index: 1, leftover_singular_value: 0 })).toBe("0.00");
  });

  it("omits leftover-map singular values that are missing, non-finite, or negative", () => {
    expect(leftoverMapAxisBadgeSingular({ axis_index: 1 })).toBeNull();
    expect(
      leftoverMapAxisBadgeSingular({ axis_index: 1, leftover_singular_value: Number.NaN }),
    ).toBeNull();
    expect(
      leftoverMapAxisBadgeSingular({ axis_index: 1, leftover_singular_value: Number.POSITIVE_INFINITY }),
    ).toBeNull();
    expect(
      leftoverMapAxisBadgeSingular({ axis_index: 1, leftover_singular_value: -0.01 }),
    ).toBeNull();
  });

  it("does not invent leftover-map singular values from leftover-map axis share", () => {
    expect(leftoverMapAxisBadgeSingular({ axis_index: 1 })).toBeNull();
  });

  it("stays distinct from leftover-map graphic and comparison graphic leftover-map axis σ copy", () => {
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).toBe("leftover axis {axis} σ {value} {share}%");
    expect(LEFTOVER_MAP_AXIS_BADGE_SHARE).toBe("leftover axis {axis} {share}%");
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
    );
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe("leftover axis {axis} σ {value}");
  });
});
