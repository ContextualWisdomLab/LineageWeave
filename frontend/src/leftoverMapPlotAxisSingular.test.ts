import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapPlotAxisSingular,
  leftoverMapCompareAxisBadge,
  leftoverMapComparePlotAxisBadge,
  leftoverMapComparePlotTickAxisBadge,
  leftoverMapPlotAxisBadge,
  leftoverMapPlotTickAxisBadge,
  leftoverSingularForAxis,
  LEFTOVER_MAP_COMPARE_AXIS_CAPTION,
  LEFTOVER_MAP_COMPARE_AXIS_LABEL,
  LEFTOVER_MAP_COMPARE_AXIS_SHARE,
  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE,
  LEFTOVER_MAP_PLOT_TICK_SINGULAR,
} from "./leftoverMapPlotAxisSingular";
import {
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
  LEFTOVER_MAP_PLOT_AXIS_SHARE,
} from "./leftoverMapPlotAxisShare";
import { LEFTOVER_MAP_COMPARE_PLOT_TICK, LEFTOVER_MAP_PLOT_TICK } from "./leftoverMapPlotLayout";
import { LEFTOVER_MAP_AXIS_BADGE_SINGULAR, LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY } from "./leftoverMapAxisBadge";

describe("leftoverSingularForAxis", () => {
  const axes = [
    { axis_index: 1, leftover_singular_value: 1.84 },
    { axis_index: 2, leftover_singular_value: 0.86 },
  ];

  it("reads persisted leftover-map singular values without inventing a leftover score", () => {
    expect(leftoverSingularForAxis(axes, 1)).toBe(1.84);
    expect(leftoverSingularForAxis(axes, 2)).toBe(0.86);
  });

  it("names a rank-0 zero leftover-map singular value", () => {
    expect(
      leftoverSingularForAxis(
        [
          { axis_index: 1, leftover_singular_value: 0 },
          { axis_index: 2, leftover_singular_value: 0 },
        ],
        1,
      ),
    ).toBe(0);
  });

  it("omits a leftover-map axis when singular value is missing, non-finite, or negative", () => {
    expect(leftoverSingularForAxis(undefined, 1)).toBeNull();
    expect(leftoverSingularForAxis([], 1)).toBeNull();
    expect(leftoverSingularForAxis([{ axis_index: 1, leftover_singular_value: null }], 1)).toBeNull();
    expect(
      leftoverSingularForAxis([{ axis_index: 1, leftover_singular_value: Number.NaN }], 1),
    ).toBeNull();
    expect(
      leftoverSingularForAxis(
        [{ axis_index: 1, leftover_singular_value: Number.POSITIVE_INFINITY }],
        1,
      ),
    ).toBeNull();
    expect(leftoverSingularForAxis([{ axis_index: 1, leftover_singular_value: -0.01 }], 1)).toBeNull();
    expect(leftoverSingularForAxis(axes, 3)).toBeNull();
  });

  it("does not invent leftover-map singular values from leftover-map axis share", () => {
    expect(leftoverSingularForAxis([{ axis_index: 1 }], 1)).toBeNull();
  });
});

describe("formatLeftoverMapPlotAxisSingular", () => {
  it("formats persisted leftover-map singular values without inventing a leftover score", () => {
    expect(formatLeftoverMapPlotAxisSingular(1.84)).toBe("1.84");
    expect(formatLeftoverMapPlotAxisSingular(0.86)).toBe("0.86");
    expect(formatLeftoverMapPlotAxisSingular(0)).toBe("0.00");
  });

  it("omits leftover-map singular values when the value is missing, non-finite, or negative", () => {
    expect(formatLeftoverMapPlotAxisSingular(null)).toBeNull();
    expect(formatLeftoverMapPlotAxisSingular(undefined)).toBeNull();
    expect(formatLeftoverMapPlotAxisSingular(Number.NaN)).toBeNull();
    expect(formatLeftoverMapPlotAxisSingular(Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapPlotAxisSingular(Number.NEGATIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapPlotAxisSingular(-0.01)).toBeNull();
  });
});

describe("leftover map comparison graphic leftover-map axis singular labels", () => {
  it("stays distinct from leftover-map graphic axis singular copy and comparison axis share", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR).toBe(
      "leftover map comparison graphic leftover-map axis {axis} σ {value}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE).toBe(
      "leftover map comparison graphic leftover-map axis {axis} σ {value} ({share}%)",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE).not.toBe(
      LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE,
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_TICK);
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR).not.toBe("leftover axis {axis} σ {value}");
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE).not.toBe(
      "leftover axis {axis} σ {value} {share}%",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR);
  });
});

describe("leftover map comparison leftover-axis report badges", () => {
  it("names persisted leftover-map singular values on leftover-axis report badges", () => {
    expect(leftoverMapCompareAxisBadge(1, 1.84, 0.82)).toEqual({
      key: LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE,
      values: { axis: 1, value: "1.84", share: "82" },
    });
    expect(leftoverMapCompareAxisBadge(2, 0.86, 0.18)).toEqual({
      key: LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE,
      values: { axis: 2, value: "0.86", share: "18" },
    });
  });

  it("names rank-0 zero leftover-map singular values on leftover-axis report badges", () => {
    expect(leftoverMapCompareAxisBadge(1, 0, 0)).toEqual({
      key: LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE,
      values: { axis: 1, value: "0.00", share: "0" },
    });
  });

  it("omits leftover-map singular values independently of leftover-map axis share", () => {
    expect(leftoverMapCompareAxisBadge(1, Number.NaN, 0.82)).toEqual({
      key: LEFTOVER_MAP_COMPARE_AXIS_SHARE,
      values: { axis: 1, share: "82" },
    });
    expect(leftoverMapCompareAxisBadge(2, -0.01, 0.18)).toEqual({
      key: LEFTOVER_MAP_COMPARE_AXIS_SHARE,
      values: { axis: 2, share: "18" },
    });
    expect(leftoverMapCompareAxisBadge(1, 1.84, Number.NaN)).toEqual({
      key: LEFTOVER_MAP_COMPARE_AXIS_SINGULAR,
      values: { axis: 1, value: "1.84" },
    });
    expect(leftoverMapCompareAxisBadge(1, null, null)).toBeNull();
  });

  it("does not invent leftover-map singular values from leftover-map axis share", () => {
    expect(leftoverMapCompareAxisBadge(1, undefined, 0.82)?.key).toBe(
      LEFTOVER_MAP_COMPARE_AXIS_SHARE,
    );
    expect(leftoverMapCompareAxisBadge(1, undefined, 0.82)?.values.value).toBeUndefined();
  });

  it("stays distinct from leftover-axis, leftover-map graphic, and comparison graphic copy", () => {
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR).toBe(
      "leftover map comparison leftover axis {axis} σ {value}",
    );
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE).toBe(
      "leftover map comparison leftover axis {axis} σ {value} {share}%",
    );
    expect(LEFTOVER_MAP_COMPARE_AXIS_SHARE).toBe(
      "leftover map comparison leftover axis {axis} {share}%",
    );
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
    );
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR).not.toBe("leftover axis {axis} σ {value}");
    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE).not.toBe(LEFTOVER_MAP_AXIS_BADGE_SINGULAR);
    expect(LEFTOVER_MAP_COMPARE_AXIS_SHARE).not.toBe("leftover axis {axis} {share}%");
    expect(LEFTOVER_MAP_COMPARE_AXIS_SHARE).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE);
    expect(LEFTOVER_MAP_COMPARE_AXIS_LABEL).not.toBe("Leftover-map axis share");
    expect(LEFTOVER_MAP_COMPARE_AXIS_CAPTION).toContain("Open a leftover pair");
  });
});

describe("leftover-map graphic-display axis singular badges", () => {
  it("names persisted leftover-map singular values on leftover-map graphic-display axes", () => {
    expect(leftoverMapPlotAxisBadge(1, 1.84, 0.82)).toEqual({
      key: LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE,
      values: { axis: 1, value: "1.84", share: "82" },
    });
    expect(leftoverMapPlotAxisBadge(2, 0.86, 0.18)).toEqual({
      key: LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE,
      values: { axis: 2, value: "0.86", share: "18" },
    });
  });

  it("names rank-0 zero leftover-map singular values on leftover-map graphic-display axes", () => {
    expect(leftoverMapPlotAxisBadge(1, 0, 0)).toEqual({
      key: LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE,
      values: { axis: 1, value: "0.00", share: "0" },
    });
  });

  it("omits leftover-map singular values independently of leftover-map axis share", () => {
    expect(leftoverMapPlotAxisBadge(1, Number.NaN, 0.82)).toEqual({
      key: LEFTOVER_MAP_PLOT_AXIS_SHARE,
      values: { axis: 1, share: "82" },
    });
    expect(leftoverMapPlotAxisBadge(2, -0.01, 0.18)).toEqual({
      key: LEFTOVER_MAP_PLOT_AXIS_SHARE,
      values: { axis: 2, share: "18" },
    });
    expect(leftoverMapPlotAxisBadge(1, 1.84, Number.NaN)).toEqual({
      key: LEFTOVER_MAP_PLOT_AXIS_SINGULAR,
      values: { axis: 1, value: "1.84" },
    });
    expect(leftoverMapPlotAxisBadge(1, null, null)).toBeNull();
  });

  it("does not invent leftover-map singular values from leftover-map axis share", () => {
    expect(leftoverMapPlotAxisBadge(1, undefined, 0.82)?.key).toBe(LEFTOVER_MAP_PLOT_AXIS_SHARE);
    expect(leftoverMapPlotAxisBadge(1, undefined, 0.82)?.values.value).toBeUndefined();
  });

  it("stays distinct from leftover-axis, comparison leftover-axis, and comparison graphic copy", () => {
    expect(LEFTOVER_MAP_PLOT_AXIS_SINGULAR).toBe("leftover-map axis {axis} σ {value}");
    expect(LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE).toBe(
      "leftover-map axis {axis} σ {value} ({share}%)",
    );
    expect(LEFTOVER_MAP_PLOT_AXIS_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
    );
    expect(LEFTOVER_MAP_PLOT_AXIS_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_PLOT_AXIS_SINGULAR).not.toBe(LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY);
    expect(LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE).not.toBe(LEFTOVER_MAP_AXIS_BADGE_SINGULAR);
    expect(LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SHARE);
  });
});

describe("leftover-map comparison graphic leftover-map axis singular badges", () => {
  it("names persisted leftover-map singular values on leftover-map comparison graphic leftover-map axes", () => {
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, 0.82)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
      values: { axis: 1, value: "1.84", share: "82" },
    });
    expect(leftoverMapComparePlotAxisBadge(2, 0.86, 0.18)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
      values: { axis: 2, value: "0.86", share: "18" },
    });
  });

  it("names rank-0 zero leftover-map singular values on leftover-map comparison graphic leftover-map axes", () => {
    expect(leftoverMapComparePlotAxisBadge(1, 0, 0)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
      values: { axis: 1, value: "0.00", share: "0" },
    });
  });

  it("omits leftover-map singular values independently of leftover-map axis share", () => {
    expect(leftoverMapComparePlotAxisBadge(1, Number.NaN, 0.82)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
      values: { axis: 1, share: "82" },
    });
    expect(leftoverMapComparePlotAxisBadge(2, -0.01, 0.18)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
      values: { axis: 2, share: "18" },
    });
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, Number.NaN)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
      values: { axis: 1, value: "1.84" },
    });
    expect(leftoverMapComparePlotAxisBadge(1, null, null)).toBeNull();
  });

  it("does not invent leftover-map singular values from leftover-map axis share", () => {
    expect(leftoverMapComparePlotAxisBadge(1, undefined, 0.82)?.key).toBe(
      LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
    );
    expect(leftoverMapComparePlotAxisBadge(1, undefined, 0.82)?.values.value).toBeUndefined();
  });

  it("does not invent leftover-map axis share from leftover-map singular values", () => {
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, undefined)?.key).toBe(
      LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
    );
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, undefined)?.values.share).toBeUndefined();
  });

  it("stays distinct from leftover-axis, leftover-map graphic, and comparison leftover-axis copy", () => {
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, 0.82)?.key).not.toBe(
      leftoverMapPlotAxisBadge(1, 1.84, 0.82)?.key,
    );
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, 0.82)?.key).not.toBe(
      leftoverMapCompareAxisBadge(1, 1.84, 0.82)?.key,
    );
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, null)?.key).not.toBe(
      leftoverMapPlotAxisBadge(1, 1.84, null)?.key,
    );
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, null)?.key).not.toBe(
      leftoverMapCompareAxisBadge(1, 1.84, null)?.key,
    );
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, null)?.key).not.toBe(
      LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY,
    );
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, 0.82)?.key).not.toBe(
      LEFTOVER_MAP_AXIS_BADGE_SINGULAR,
    );
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, null)?.key).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_TICK);
    expect(leftoverMapComparePlotAxisBadge(1, 1.84, 0.82)?.key).toBe(
      LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
    );
  });
});

describe("leftover-map graphic leftover-map axis tick leftover-map singular values", () => {
  it("names persisted leftover-map singular values on leftover-map graphic leftover-map axis ticks", () => {
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", 1.84)).toEqual({
      key: LEFTOVER_MAP_PLOT_TICK_SINGULAR,
      values: { axis: 1, value: "+0.50", singular: "1.84" },
    });
    expect(leftoverMapPlotTickAxisBadge(2, "−0.02", 0.86)).toEqual({
      key: LEFTOVER_MAP_PLOT_TICK_SINGULAR,
      values: { axis: 2, value: "−0.02", singular: "0.86" },
    });
  });

  it("names rank-0 zero leftover-map singular values on leftover-map graphic leftover-map axis ticks", () => {
    expect(leftoverMapPlotTickAxisBadge(1, "0.00", 0)).toEqual({
      key: LEFTOVER_MAP_PLOT_TICK_SINGULAR,
      values: { axis: 1, value: "0.00", singular: "0.00" },
    });
  });

  it("omits leftover-map singular values independently of leftover-map axis share", () => {
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", Number.NaN)).toEqual({
      key: LEFTOVER_MAP_PLOT_TICK,
      values: { axis: 1, value: "+0.50" },
    });
    expect(leftoverMapPlotTickAxisBadge(2, "−0.02", -0.01)).toEqual({
      key: LEFTOVER_MAP_PLOT_TICK,
      values: { axis: 2, value: "−0.02" },
    });
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", 1.84).values.share).toBeUndefined();
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", null)).toEqual({
      key: LEFTOVER_MAP_PLOT_TICK,
      values: { axis: 1, value: "+0.50" },
    });
  });

  it("does not invent leftover-map singular values from leftover-map axis share", () => {
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", undefined).key).toBe(LEFTOVER_MAP_PLOT_TICK);
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", undefined).values.singular).toBeUndefined();
  });

  it("does not invent leftover-map axis share from leftover-map singular values", () => {
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", 1.84).key).toBe(LEFTOVER_MAP_PLOT_TICK_SINGULAR);
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", 1.84).values.share).toBeUndefined();
  });

  it("stays distinct from leftover-axis, leftover-map graphic axis, comparison leftover-axis, and comparison graphic copy", () => {
    expect(LEFTOVER_MAP_PLOT_TICK_SINGULAR).toBe("leftover-map axis {axis} tick {value} σ {singular}");
    expect(LEFTOVER_MAP_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_TICK);
    expect(LEFTOVER_MAP_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY);
    expect(LEFTOVER_MAP_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_TICK);
    expect(LEFTOVER_MAP_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR);
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapPlotAxisBadge(1, 1.84, null)?.key,
    );
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapComparePlotAxisBadge(1, 1.84, null)?.key,
    );
    expect(leftoverMapPlotTickAxisBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapComparePlotTickAxisBadge(1, "+0.50", 1.84).key,
    );
  });
});

describe("leftover-map comparison graphic leftover-map axis tick leftover-map singular values", () => {
  it("names persisted leftover-map singular values on leftover-map comparison graphic leftover-map axis ticks", () => {
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", 1.84)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR,
      values: { axis: 1, value: "+0.50", singular: "1.84" },
    });
    expect(leftoverMapComparePlotTickAxisBadge(2, "−0.02", 0.86)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR,
      values: { axis: 2, value: "−0.02", singular: "0.86" },
    });
  });

  it("names rank-0 zero leftover-map singular values on leftover-map comparison graphic leftover-map axis ticks", () => {
    expect(leftoverMapComparePlotTickAxisBadge(1, "0.00", 0)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR,
      values: { axis: 1, value: "0.00", singular: "0.00" },
    });
  });

  it("omits leftover-map singular values independently of leftover-map axis share", () => {
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", Number.NaN)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_TICK,
      values: { axis: 1, value: "+0.50" },
    });
    expect(leftoverMapComparePlotTickAxisBadge(2, "−0.02", -0.01)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_TICK,
      values: { axis: 2, value: "−0.02" },
    });
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", 1.84).values.share).toBeUndefined();
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", null)).toEqual({
      key: LEFTOVER_MAP_COMPARE_PLOT_TICK,
      values: { axis: 1, value: "+0.50" },
    });
  });

  it("does not invent leftover-map singular values from leftover-map axis share", () => {
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", undefined).key).toBe(
      LEFTOVER_MAP_COMPARE_PLOT_TICK,
    );
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", undefined).values.singular).toBeUndefined();
  });

  it("does not invent leftover-map axis share from leftover-map singular values", () => {
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", 1.84).key).toBe(
      LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR,
    );
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", 1.84).values.share).toBeUndefined();
  });

  it("stays distinct from leftover-axis, leftover-map graphic axis, leftover-map graphic tick, comparison leftover-axis, and comparison graphic copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR).toBe(
      "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular}",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_TICK);
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_TICK_SINGULAR);
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_TICK);
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR);
    expect(LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR).not.toBe(LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY);
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapPlotTickAxisBadge(1, "+0.50", 1.84).key,
    );
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapComparePlotAxisBadge(1, 1.84, null)?.key,
    );
    expect(leftoverMapComparePlotTickAxisBadge(1, "+0.50", 1.84).key).not.toBe(
      leftoverMapPlotAxisBadge(1, 1.84, null)?.key,
    );
  });
});
