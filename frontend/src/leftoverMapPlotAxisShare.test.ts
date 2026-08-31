import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapPlotAxisShare,
  leftoverShareForAxis,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_1,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_2,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE,
  LEFTOVER_MAP_PLOT_AXIS_SHARE,
} from "./leftoverMapPlotAxisShare";
import {
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
} from "./leftoverMapPlotAxisSingular";

describe("leftoverShareForAxis", () => {
  const axes = [
    { axis_index: 1, leftover_share: 0.82 },
    { axis_index: 2, leftover_share: 0.18 },
  ];

  it("reads persisted leftover-map axis share without inventing a leftover score", () => {
    expect(leftoverShareForAxis(axes, 1)).toBe(0.82);
    expect(leftoverShareForAxis(axes, 2)).toBe(0.18);
  });

  it("names a rank-0 zero-share leftover-map axis", () => {
    expect(leftoverShareForAxis([{ axis_index: 1, leftover_share: 0 }, { axis_index: 2, leftover_share: 0 }], 1)).toBe(
      0,
    );
  });

  it("omits a leftover-map axis when share is missing or non-finite", () => {
    expect(leftoverShareForAxis(undefined, 1)).toBeNull();
    expect(leftoverShareForAxis([], 1)).toBeNull();
    expect(leftoverShareForAxis([{ axis_index: 1, leftover_share: null }], 1)).toBeNull();
    expect(leftoverShareForAxis([{ axis_index: 1, leftover_share: Number.NaN }], 1)).toBeNull();
    expect(
      leftoverShareForAxis([{ axis_index: 1, leftover_share: Number.POSITIVE_INFINITY }], 1),
    ).toBeNull();
    expect(leftoverShareForAxis(axes, 3)).toBeNull();
  });
});

describe("formatLeftoverMapPlotAxisShare", () => {
  it("formats persisted leftover-map axis share as percent without inventing a leftover score", () => {
    expect(formatLeftoverMapPlotAxisShare(0.82)).toBe("82");
    expect(formatLeftoverMapPlotAxisShare(0.18)).toBe("18");
    expect(formatLeftoverMapPlotAxisShare(0)).toBe("0");
  });

  it("omits leftover-map axis share when the value is missing or non-finite", () => {
    expect(formatLeftoverMapPlotAxisShare(null)).toBeNull();
    expect(formatLeftoverMapPlotAxisShare(undefined)).toBeNull();
    expect(formatLeftoverMapPlotAxisShare(Number.NaN)).toBeNull();
    expect(formatLeftoverMapPlotAxisShare(Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapPlotAxisShare(Number.NEGATIVE_INFINITY)).toBeNull();
  });
});

describe("leftover map comparison axis share labels", () => {
  it("stays distinct from leftover-map graphic axis share copy", () => {
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE).toBe(
      "leftover map comparison axis {axis} ({share}%)",
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_1).toBe("leftover map comparison axis 1");
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_2).toBe("leftover map comparison axis 2");
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE).not.toBe(LEFTOVER_MAP_PLOT_AXIS_SHARE);
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_1).not.toBe("leftover-map axis 1");
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_2).not.toBe("leftover-map axis 2");
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE).not.toBe(
      LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
    );
    expect(LEFTOVER_MAP_COMPARE_PLOT_AXIS_1).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR);
  });
});
