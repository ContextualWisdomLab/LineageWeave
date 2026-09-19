import { describe, expect, it } from "vitest";
import {
  LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK,
  LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR,
  LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR_SHARE,
  LEFTOVER_MAP_COMPARE_PLOT_TICK,
  leftoverMapComparePlotTickAxisBadge,
  leftoverMapPlotTickIsOrigin,
} from "./leftoverMapPlotAxisSingular";

describe("comparison-graphic origin tick projection", () => {
  it("recognizes only the canonical formatted zero coordinate as origin", () => {
    expect(leftoverMapPlotTickIsOrigin("0.00")).toBe(true);
    expect(leftoverMapPlotTickIsOrigin("+0.00")).toBe(false);
    expect(leftoverMapPlotTickIsOrigin("−0.00")).toBe(false);
    expect(leftoverMapPlotTickIsOrigin("0")).toBe(false);
  });

  it("keeps origin identity independent from persisted share and singular evidence", () => {
    expect(leftoverMapComparePlotTickAxisBadge(1, "0.00", null, null).template).toBe(
      LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK,
    );
    expect(leftoverMapComparePlotTickAxisBadge(1, "0.00", null, 0.25).template).toBe(
      LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SHARE,
    );
    expect(leftoverMapComparePlotTickAxisBadge(1, "0.00", 1.5, null).template).toBe(
      LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR,
    );
    expect(leftoverMapComparePlotTickAxisBadge(1, "0.00", 1.5, 0.25).template).toBe(
      LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK_SINGULAR_SHARE,
    );
  });

  it("fails invalid evidence closed without turning a non-origin tick into origin", () => {
    const badge = leftoverMapComparePlotTickAxisBadge(
      2,
      "+0.50",
      Number.NaN,
      Number.POSITIVE_INFINITY,
    );

    expect(badge).toEqual({
      template: LEFTOVER_MAP_COMPARE_PLOT_TICK,
      values: { axis: 2, value: "+0.50" },
    });
  });
});
