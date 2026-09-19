import { describe, expect, it } from "vitest";
import {
  leftoverMapCompareAxisTickBadge,
  leftoverMapComparePlotTickAxisBadge,
  leftoverMapPlotTickAxisBadge,
  LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_TICK_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR_SHARE,
  LEFTOVER_MAP_PLOT_TICK_SHARE,
  LEFTOVER_MAP_PLOT_TICK_SINGULAR,
  LEFTOVER_MAP_PLOT_TICK_SINGULAR_SHARE,
} from "./leftoverMapPlotAxisSingular";

describe("leftoverMapPlotTickAxisBadge", () => {
  it("keeps report-graphic tick singular and share evidence independent", () => {
    expect(leftoverMapPlotTickAxisBadge(1, "-1.0", null, null)).toBeNull();
    expect(leftoverMapPlotTickAxisBadge(1, "-1.0", 1.24, null)).toEqual({
      template: LEFTOVER_MAP_PLOT_TICK_SINGULAR,
      values: { axis: 1, value: "-1.0", singular: "1.24" },
    });
    expect(leftoverMapPlotTickAxisBadge(2, "0.5", null, 0.18)).toEqual({
      template: LEFTOVER_MAP_PLOT_TICK_SHARE,
      values: { axis: 2, value: "0.5", share: "18" },
    });
    expect(leftoverMapPlotTickAxisBadge(2, "0.5", 0, 0.18)).toEqual({
      template: LEFTOVER_MAP_PLOT_TICK_SINGULAR_SHARE,
      values: { axis: 2, value: "0.5", singular: "0.00", share: "18" },
    });
  });

  it("fails closed for invalid persisted tick evidence without fabricating the other field", () => {
    expect(
      leftoverMapPlotTickAxisBadge(1, "0", Number.NaN, Number.POSITIVE_INFINITY),
    ).toBeNull();
    expect(leftoverMapPlotTickAxisBadge(1, "0", -0.01, 0.42)).toEqual({
      template: LEFTOVER_MAP_PLOT_TICK_SHARE,
      values: { axis: 1, value: "0", share: "42" },
    });
  });
});

describe("leftoverMapComparePlotTickAxisBadge", () => {
  it("keeps comparison-graphic tick singular and share evidence independent", () => {
    expect(leftoverMapComparePlotTickAxisBadge(1, "-1.0", null, null)).toBeNull();
    expect(leftoverMapComparePlotTickAxisBadge(1, "-1.0", 1.24, null)).toEqual({
      template: LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR,
      values: { axis: 1, value: "-1.0", singular: "1.24" },
    });
    expect(leftoverMapComparePlotTickAxisBadge(2, "0.5", null, 0.18)).toEqual({
      template: LEFTOVER_MAP_COMPARE_PLOT_TICK_SHARE,
      values: { axis: 2, value: "0.5", share: "18" },
    });
    expect(leftoverMapComparePlotTickAxisBadge(2, "0.5", 0, 0.18)).toEqual({
      template: LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR_SHARE,
      values: { axis: 2, value: "0.5", singular: "0.00", share: "18" },
    });
  });
});

describe("leftoverMapCompareAxisTickBadge", () => {
  it("projects only finite persisted singular evidence onto comparison-strip ticks", () => {
    expect(leftoverMapCompareAxisTickBadge(1, "0", 1.24)).toEqual({
      template: LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR,
      values: { axis: 1, value: "0", singular: "1.24" },
    });
    expect(leftoverMapCompareAxisTickBadge(2, "1", 0)).toEqual({
      template: LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR,
      values: { axis: 2, value: "1", singular: "0.00" },
    });
    expect(leftoverMapCompareAxisTickBadge(1, "0", null)).toBeNull();
    expect(leftoverMapCompareAxisTickBadge(1, "0", Number.NaN)).toBeNull();
    expect(leftoverMapCompareAxisTickBadge(1, "0", -0.01)).toBeNull();
  });
});
