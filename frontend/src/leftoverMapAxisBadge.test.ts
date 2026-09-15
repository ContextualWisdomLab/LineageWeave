import { describe, expect, it } from "vitest";
import {
  leftoverMapAxisBadge,
  leftoverMapAxisBadgeShare,
  leftoverMapAxisBadgeSingular,
  LEFTOVER_MAP_AXIS_BADGE_SHARE,
  LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
  LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY,
} from "./leftoverMapAxisBadge";
import { LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE } from "./leftoverMapPlotAxisShare";
import {
  leftoverMapCompareAxisBadge,
  leftoverMapComparePlotAxisBadge,
  LEFTOVER_MAP_COMPARE_AXIS_SHARE,
  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE,
} from "./leftoverMapPlotAxisSingular";

describe("leftoverMapAxisBadgeShare", () => {
  it("formats report-axis share as an optional suffix", () => {
    expect(leftoverMapAxisBadgeShare(0.82)).toBe(" 82%");
    expect(leftoverMapAxisBadgeShare(0.18)).toBe(" 18%");
    expect(leftoverMapAxisBadgeShare(0)).toBe(" 0%");
    expect(leftoverMapAxisBadgeShare(undefined)).toBe("");
    expect(leftoverMapAxisBadgeShare(Number.NaN)).toBe("");
    expect(leftoverMapAxisBadgeShare(Number.POSITIVE_INFINITY)).toBe("");
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

  it("keeps report copy distinct from plot and comparison copy", () => {
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).toBe("leftover axis {axis} σ {value}{share}");
    expect(LEFTOVER_MAP_AXIS_BADGE_SHARE).toBe("leftover axis {axis}{share}");
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY).toBe("leftover axis {axis} σ {value}");
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
    );
  });
});

describe("leftoverMapAxisBadge", () => {
  it("keeps singular-only, share-only, combined, and empty states independent", () => {
    expect(
      leftoverMapAxisBadge({
        axis_index: 1,
        leftover_singular_value: 1.24,
        leftover_share: 0.42,
      }),
    ).toEqual({
      template: LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
      values: { axis: 1, value: "1.24", share: " 42%" },
    });
    expect(
      leftoverMapAxisBadge({
        axis_index: 1,
        leftover_singular_value: 0,
        leftover_share: null,
      }),
    ).toEqual({
      template: LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY,
      values: { axis: 1, value: "0.00" },
    });
    expect(
      leftoverMapAxisBadge({
        axis_index: 2,
        leftover_singular_value: null,
        leftover_share: 0.18,
      }),
    ).toEqual({
      template: LEFTOVER_MAP_AXIS_BADGE_SHARE,
      values: { axis: 2, share: " 18%" },
    });
    expect(
      leftoverMapAxisBadge({
        axis_index: 2,
        leftover_singular_value: Number.NaN,
        leftover_share: Number.POSITIVE_INFINITY,
      }),
    ).toBeNull();
  });
});

describe("leftoverMapComparePlotAxisBadge", () => {
  it("returns no graphic badge when neither persisted measure is usable", () => {
    expect(
      leftoverMapComparePlotAxisBadge({
        axis_index: 1,
        leftover_singular_value: Number.NaN,
        leftover_share: Number.POSITIVE_INFINITY,
      }),
    ).toBeNull();
  });

  it("keeps graphic share-only evidence independent", () => {
    expect(
      leftoverMapComparePlotAxisBadge({
        axis_index: 2,
        leftover_singular_value: null,
        leftover_share: 0.18,
      }),
    ).toEqual({
      template: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
      values: { axis: 2, share: "18" },
    });
  });

  it("keeps graphic singular-only evidence independent and preserves finite zero", () => {
    expect(
      leftoverMapComparePlotAxisBadge({
        axis_index: 1,
        leftover_singular_value: 0,
        leftover_share: null,
      }),
    ).toEqual({
      template: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
      values: { axis: 1, value: "0.00" },
    });
  });

  it("combines persisted graphic singular and share evidence without deriving either", () => {
    expect(
      leftoverMapComparePlotAxisBadge({
        axis_index: 1,
        leftover_singular_value: 1.24,
        leftover_share: 0.42,
      }),
    ).toEqual({
      template: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
      values: { axis: 1, value: "1.24", share: "42" },
    });
  });
});

describe("leftoverMapCompareAxisBadge", () => {
  it("keeps persisted singular and share evidence independent", () => {
    expect(
      leftoverMapCompareAxisBadge({
        axis_index: 1,
        leftover_singular_value: 1.24,
        leftover_share: 0.42,
      }),
    ).toEqual({
      template: LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE,
      values: { axis: 1, value: "1.24", share: "42" },
    });
    expect(
      leftoverMapCompareAxisBadge({
        axis_index: 1,
        leftover_singular_value: 0,
        leftover_share: null,
      }),
    ).toEqual({
      template: LEFTOVER_MAP_COMPARE_AXIS_SINGULAR,
      values: { axis: 1, value: "0.00" },
    });
    expect(
      leftoverMapCompareAxisBadge({
        axis_index: 2,
        leftover_singular_value: null,
        leftover_share: 0.18,
      }),
    ).toEqual({
      template: LEFTOVER_MAP_COMPARE_AXIS_SHARE,
      values: { axis: 2, share: "18" },
    });
  });

  it("omits the comparison-strip badge when neither persisted measure is usable", () => {
    expect(
      leftoverMapCompareAxisBadge({
        axis_index: 1,
        leftover_singular_value: Number.NaN,
        leftover_share: Number.POSITIVE_INFINITY,
      }),
    ).toBeNull();
  });
});
