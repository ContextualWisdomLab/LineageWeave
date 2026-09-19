import { describe, expect, it } from "vitest";
import {
  LEFTOVER_MAP_AXIS_TICK_SHARE,
  LEFTOVER_MAP_AXIS_TICK_SINGULAR,
  LEFTOVER_MAP_AXIS_TICK_SINGULAR_SHARE,
  leftoverMapAxisTickBadge,
} from "./leftoverMapAxisBadge";

describe("leftoverMapAxisTickBadge", () => {
  it("keeps persisted singular and share evidence independently observable", () => {
    expect(leftoverMapAxisTickBadge(1, "0.25", 0.5, 0.4)).toEqual({
      template: LEFTOVER_MAP_AXIS_TICK_SINGULAR_SHARE,
      values: { axis: 1, value: "0.25", singular: "0.50", share: "40" },
    });
    expect(leftoverMapAxisTickBadge(1, "0.00", 0, null)).toEqual({
      template: LEFTOVER_MAP_AXIS_TICK_SINGULAR,
      values: { axis: 1, value: "0.00", singular: "0.00" },
    });
    expect(leftoverMapAxisTickBadge(2, "−0.25", null, 0.4)).toEqual({
      template: LEFTOVER_MAP_AXIS_TICK_SHARE,
      values: { axis: 2, value: "−0.25", share: "40" },
    });
  });

  it("fails closed when neither persisted evidence value is usable", () => {
    expect(
      leftoverMapAxisTickBadge(1, "0.25", Number.NaN, Number.POSITIVE_INFINITY),
    ).toBeNull();
    expect(leftoverMapAxisTickBadge(1, "0.25", null, undefined)).toBeNull();
  });
});
