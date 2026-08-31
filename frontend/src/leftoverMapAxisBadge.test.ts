import { describe, expect, it } from "vitest";
import {
  leftoverMapAxisBadge,
  leftoverMapAxisBadgeShare,
  leftoverMapAxisBadgeSingular,
  leftoverMapAxisTickBadge,
  LEFTOVER_MAP_AXIS_BADGE_SHARE,
  LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
  LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY,
  LEFTOVER_MAP_AXIS_TICK,
  LEFTOVER_MAP_AXIS_TICK_SINGULAR,
} from "./leftoverMapAxisBadge";
import {
  leftoverMapCompareAxisTickBadge,
  leftoverMapComparePlotTickAxisBadge,
  leftoverMapPlotTickAxisBadge,
  LEFTOVER_MAP_COMPARE_AXIS_SHARE,
  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE,
  LEFTOVER_MAP_COMPARE_AXIS_TICK,
  LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE,
  LEFTOVER_MAP_PLOT_TICK_SINGULAR,
} from "./leftoverMapPlotAxisSingular";

describe("leftoverMapAxisBadgeShare", () => {
  it("formats leftover-axis share percent without inventing a leftover score", () => {
    expect(leftoverMapAxisBadgeShare(0.82)).toBe("82");
    expect(leftoverMapAxisBadgeShare(0.18)).toBe("18");
    expect(leftoverMapAxisBadgeShare(0)).toBe("0");
  });

  it("omits leftover-map axis share that is missing or non-finite", () => {
    expect(leftoverMapAxisBadgeShare(undefined)).toBeNull();
    expect(leftoverMapAxisBadgeShare(null)).toBeNull();
    expect(leftoverMapAxisBadgeShare(Number.NaN)).toBeNull();
    expect(leftoverMapAxisBadgeShare(Number.POSITIVE_INFINITY)).toBeNull();
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

  it("stays distinct from leftover-map graphic and comparison leftover-axis σ copy", () => {
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).toBe("leftover axis {axis} σ {value} {share}%");
    expect(LEFTOVER_MAP_AXIS_BADGE_SHARE).toBe("leftover axis {axis} {share}%");
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY).toBe("leftover axis {axis} σ {value}");
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
    );
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE);
    expect(LEFTOVER_MAP_AXIS_BADGE_SHARE).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_SHARE);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR).not.toBe(LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR);
  });
});

describe("leftover-axis report badge leftover-map singular values", () => {
  it("names persisted leftover-map singular values with leftover-map axis share", () => {
    expect(leftoverMapAxisBadge(1, 1.84, 0.82)).toEqual({
      key: LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
      values: { axis: 1, value: "1.84", share: "82" },
    });
    expect(leftoverMapAxisBadge(2, 0.86, 0.18)).toEqual({
      key: LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
      values: { axis: 2, value: "0.86", share: "18" },
    });
  });

  it("names rank-0 zero leftover-map singular values on leftover-axis report badges", () => {
    expect(leftoverMapAxisBadge(1, 0, 0)).toEqual({
      key: LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
      values: { axis: 1, value: "0.00", share: "0" },
    });
  });

  it("omits leftover-map singular values independently of leftover-map axis share", () => {
    expect(leftoverMapAxisBadge(1, Number.NaN, 0.82)).toEqual({
      key: LEFTOVER_MAP_AXIS_BADGE_SHARE,
      values: { axis: 1, share: "82" },
    });
    expect(leftoverMapAxisBadge(2, -0.01, 0.18)).toEqual({
      key: LEFTOVER_MAP_AXIS_BADGE_SHARE,
      values: { axis: 2, share: "18" },
    });
    expect(leftoverMapAxisBadge(1, 1.84, Number.NaN)).toEqual({
      key: LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY,
      values: { axis: 1, value: "1.84" },
    });
    expect(leftoverMapAxisBadge(1, null, null)).toBeNull();
  });

  it("does not invent leftover-map singular values from leftover-map axis share", () => {
    expect(leftoverMapAxisBadge(1, undefined, 0.82)?.key).toBe(LEFTOVER_MAP_AXIS_BADGE_SHARE);
    expect(leftoverMapAxisBadge(1, undefined, 0.82)?.values.value).toBeUndefined();
  });

  it("does not invent leftover-map axis share from leftover-map singular values", () => {
    expect(leftoverMapAxisBadge(1, 1.84, undefined)?.key).toBe(LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY);
    expect(leftoverMapAxisBadge(1, 1.84, undefined)?.values.share).toBeUndefined();
  });
});

describe("leftover-axis leftover-axis tick leftover-map singular values", () => {
  it("names persisted leftover-map singular values on leftover-axis ticks", () => {
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84)).toEqual({
      key: LEFTOVER_MAP_AXIS_TICK_SINGULAR,
      values: { axis: 1, value: "+0.50", singular: "1.84" },
    });
    expect(leftoverMapAxisTickBadge(2, "−0.02", 0.86)).toEqual({
      key: LEFTOVER_MAP_AXIS_TICK_SINGULAR,
      values: { axis: 2, value: "−0.02", singular: "0.86" },
    });
  });

  it("names rank-0 zero leftover-map singular values on leftover-axis ticks", () => {
    expect(leftoverMapAxisTickBadge(1, "0.00", 0)).toEqual({
      key: LEFTOVER_MAP_AXIS_TICK_SINGULAR,
      values: { axis: 1, value: "0.00", singular: "0.00" },
    });
  });

  it("omits leftover-map singular values independently of leftover-map axis share", () => {
    expect(leftoverMapAxisTickBadge(1, "+0.50", Number.NaN)).toEqual({
      key: LEFTOVER_MAP_AXIS_TICK,
      values: { axis: 1, value: "+0.50" },
    });
    expect(leftoverMapAxisTickBadge(2, "−0.02", -0.01)).toEqual({
      key: LEFTOVER_MAP_AXIS_TICK,
      values: { axis: 2, value: "−0.02" },
    });
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84).values.share).toBeUndefined();
    expect(leftoverMapAxisTickBadge(1, "+0.50", null)).toEqual({
      key: LEFTOVER_MAP_AXIS_TICK,
      values: { axis: 1, value: "+0.50" },
    });
  });

  it("does not invent leftover-map singular values from leftover-map axis share", () => {
    expect(leftoverMapAxisTickBadge(1, "+0.50", undefined).key).toBe(LEFTOVER_MAP_AXIS_TICK);
    expect(leftoverMapAxisTickBadge(1, "+0.50", undefined).values.singular).toBeUndefined();
  });

  it("does not invent leftover-map axis share from leftover-map singular values", () => {
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84).key).toBe(LEFTOVER_MAP_AXIS_TICK_SINGULAR);
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84).values.share).toBeUndefined();
  });

  it("stays distinct from leftover-map graphic tick, comparison leftover-axis tick, and leftover-axis badge copy", () => {
    expect(LEFTOVER_MAP_AXIS_TICK).toBe("leftover axis {axis} tick {value}");
    expect(LEFTOVER_MAP_AXIS_TICK_SINGULAR).toBe("leftover axis {axis} tick {value} σ {singular}");
    expect(LEFTOVER_MAP_AXIS_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_AXIS_TICK);
    expect(LEFTOVER_MAP_AXIS_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_TICK_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR);
    expect(LEFTOVER_MAP_AXIS_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY);
    expect(LEFTOVER_MAP_AXIS_TICK).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_TICK);
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapCompareAxisTickBadge(1, "+0.50", 1.84).key,
    );
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapCompareAxisTickBadge(1, "+0.50", 1.84, 0.82).key,
    );
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapPlotTickAxisBadge(1, "+0.50", 1.84).key,
    );
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapComparePlotTickAxisBadge(1, "+0.50", 1.84).key,
    );
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapComparePlotTickAxisBadge(1, "+0.50", 1.84, 0.82).key,
    );
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapPlotTickAxisBadge(1, "+0.50", 1.84, 0.82).key,
    );
    expect(leftoverMapAxisTickBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapAxisBadge(1, 1.84, null)?.key,
    );
  });
});
