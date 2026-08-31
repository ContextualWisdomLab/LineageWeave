import { describe, expect, it } from "vitest";
import {
  formatLeftoverMapPlotAxisSingular,
  leftoverSingularForAxis,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR,
  LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE,
} from "./leftoverMapPlotAxisSingular";
import { LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE } from "./leftoverMapPlotAxisShare";
import { LEFTOVER_MAP_COMPARE_PLOT_TICK } from "./leftoverMapPlotLayout";

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
  });
});
