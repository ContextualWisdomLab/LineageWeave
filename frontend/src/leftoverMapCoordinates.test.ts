import { describe, expect, it } from "vitest";
import {
  leftoverMapComparePlotCriterionBadge,
  leftoverMapComparePlotPostBadge,
  leftoverMapPlotCriterionBadge,
  leftoverMapPlotPostBadge,
  LEFTOVER_MAP_COMPARE_PLOT_CRITERION,
  LEFTOVER_MAP_COMPARE_PLOT_POST_ACTION,
  LEFTOVER_MAP_PLOT_CRITERION,
  LEFTOVER_MAP_PLOT_POST_ACTION,
} from "./leftoverMapPlotLayout";
import {
  formatLeftoverMapCoordinatePair,
  formatLeftoverMapCoordinates,
  leftoverMapCompareListPostBadge,
  leftoverMapCompareListCriterionBadge,
  leftoverMapListCriterionBadge,
  leftoverMapListPostBadge,
  LEFTOVER_MAP_COMPARE_COORDINATES_LABEL,
  LEFTOVER_MAP_COMPARE_LIST_POST_ACTION,
  LEFTOVER_MAP_COMPARE_LIST_CRITERION,
  LEFTOVER_MAP_LIST_CRITERION,
  LEFTOVER_MAP_LIST_POST_ACTION,
} from "./leftoverMapCoordinates";

describe("formatLeftoverMapCoordinates", () => {
  it("names leftover-map coordinates without inventing a leftover score", () => {
    expect(formatLeftoverMapCoordinates(0.5, 0.1, 0.5, -0.02)).toBe(
      "\u03BE (+0.50, +0.10) \u03B6 (+0.50, \u22120.02)",
    );
    expect(formatLeftoverMapCoordinates(0, 0, 0, 0)).toBe(
      "\u03BE (0.00, 0.00) \u03B6 (0.00, 0.00)",
    );
    expect(formatLeftoverMapCoordinates(-1.25, 2, 0.5, 0)).toBe(
      "\u03BE (\u22121.25, +2.00) \u03B6 (+0.50, 0.00)",
    );
  });

  it("omits the badge when any leftover-map coordinate is missing or non-finite", () => {
    expect(formatLeftoverMapCoordinates(null, 0, 0, 0)).toBeNull();
    expect(formatLeftoverMapCoordinates(0, undefined, 0, 0)).toBeNull();
    expect(formatLeftoverMapCoordinates(0, 0, Number.NaN, 0)).toBeNull();
    expect(formatLeftoverMapCoordinates(0, 0, 0, Number.POSITIVE_INFINITY)).toBeNull();
    expect(formatLeftoverMapCoordinates(0, Number.NEGATIVE_INFINITY, 0, 0)).toBeNull();
  });

  it("keeps the grouping comparison coordinates label distinct from the graphic tick label", () => {
    expect(LEFTOVER_MAP_COMPARE_COORDINATES_LABEL).toBe("Leftover map comparison coordinates");
    expect(LEFTOVER_MAP_COMPARE_COORDINATES_LABEL).not.toBe("leftover-map axis {axis} tick {value}");
  });
});

describe("formatLeftoverMapCoordinatePair", () => {
  it("names one leftover-map position without inventing a leftover score", () => {
    expect(formatLeftoverMapCoordinatePair(0.5, -0.02)).toBe("(+0.50, \u22120.02)");
    expect(formatLeftoverMapCoordinatePair(0, 0)).toBe("(0.00, 0.00)");
  });

  it("omits a pair when either leftover-map axis is missing or non-finite", () => {
    expect(formatLeftoverMapCoordinatePair(null, 0)).toBeNull();
    expect(formatLeftoverMapCoordinatePair(0, Number.NaN)).toBeNull();
  });
});

describe("leftoverMapListPostBadge", () => {
  it("names persisted leftover-map person coordinates without inventing a leftover score", () => {
    expect(leftoverMapListPostBadge("Public post", 0.5, 0.1)).toEqual({
      key: LEFTOVER_MAP_LIST_POST_ACTION,
      values: { title: "Public post", person: "(+0.50, +0.10)" },
    });
    expect(leftoverMapListPostBadge("negative", -0.7, -0.4)).toEqual({
      key: LEFTOVER_MAP_LIST_POST_ACTION,
      values: { title: "negative", person: "(\u22120.70, \u22120.40)" },
    });
  });

  it("names rank-0 origin leftover-map person coordinates as ξ (0.00, 0.00)", () => {
    expect(leftoverMapListPostBadge("Public post", 0, 0)).toEqual({
      key: LEFTOVER_MAP_LIST_POST_ACTION,
      values: { title: "Public post", person: "(0.00, 0.00)" },
    });
  });

  it("omits leftover-map person coordinates when ξ is missing or non-finite", () => {
    expect(leftoverMapListPostBadge("Public post", null, 0.1)).toBeNull();
    expect(leftoverMapListPostBadge("Public post", 0.5, undefined)).toBeNull();
    expect(leftoverMapListPostBadge("Public post", Number.NaN, 0.1)).toBeNull();
    expect(leftoverMapListPostBadge("Public post", 0.5, Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("names leftover-map pair leftover-map post leftover-map person coordinates independently of leftover-map pair leftover-map criterion leftover-map item coordinates", () => {
    expect(leftoverMapListPostBadge("Public post", 0.5, 0.1)).not.toBeNull();
    expect(formatLeftoverMapCoordinates(0.5, 0.1, null, -0.02)).toBeNull();
    expect(formatLeftoverMapCoordinates(0.5, 0.1, 0.5, Number.NaN)).toBeNull();
  });

  it("stays distinct from leftover-map graphic leftover-map post markers and leftover-map comparison graphic leftover-map post markers", () => {
    expect(LEFTOVER_MAP_LIST_POST_ACTION).toBe(
      "leftover pair leftover-map post {title} at ξ {person}",
    );
    expect(LEFTOVER_MAP_LIST_POST_ACTION).not.toBe(LEFTOVER_MAP_PLOT_POST_ACTION);
    expect(LEFTOVER_MAP_LIST_POST_ACTION).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_POST_ACTION);
    expect(LEFTOVER_MAP_LIST_POST_ACTION).not.toBe(LEFTOVER_MAP_COMPARE_LIST_POST_ACTION);
    expect(leftoverMapListPostBadge("Public post", 0.5, 0.1)?.key).not.toBe(
      leftoverMapPlotPostBadge("Public post", 0.5, 0.1)?.key ?? "",
    );
    expect(leftoverMapListPostBadge("Public post", 0.5, 0.1)?.key).not.toBe(
      leftoverMapComparePlotPostBadge("Public post", 0.5, 0.1)?.key ?? "",
    );
    expect(leftoverMapListPostBadge("Public post", 0.5, 0.1)?.key).not.toBe(
      leftoverMapCompareListPostBadge("Public post", 0.5, 0.1)?.key ?? "",
    );
  });
});

describe("leftoverMapListCriterionBadge", () => {
  it("names persisted leftover-map item coordinates without inventing a leftover score", () => {
    expect(leftoverMapListCriterionBadge("sales-lead", 0.5, -0.02)).toEqual({
      key: LEFTOVER_MAP_LIST_CRITERION,
      values: { label: "sales-lead", item: "(+0.50, \u22120.02)" },
    });
    expect(leftoverMapListCriterionBadge("negative", -0.7, -0.4)).toEqual({
      key: LEFTOVER_MAP_LIST_CRITERION,
      values: { label: "negative", item: "(\u22120.70, \u22120.40)" },
    });
  });

  it("names rank-0 origin leftover-map item coordinates as ζ (0.00, 0.00)", () => {
    expect(leftoverMapListCriterionBadge("sales-lead", 0, 0)).toEqual({
      key: LEFTOVER_MAP_LIST_CRITERION,
      values: { label: "sales-lead", item: "(0.00, 0.00)" },
    });
  });

  it("omits leftover-map item coordinates when ζ is missing or non-finite", () => {
    expect(leftoverMapListCriterionBadge("sales-lead", null, -0.02)).toBeNull();
    expect(leftoverMapListCriterionBadge("sales-lead", 0.5, undefined)).toBeNull();
    expect(leftoverMapListCriterionBadge("sales-lead", Number.NaN, -0.02)).toBeNull();
    expect(leftoverMapListCriterionBadge("sales-lead", 0.5, Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("names leftover-map pair leftover-map criterion leftover-map item coordinates independently of leftover-map pair leftover-map post leftover-map person coordinates", () => {
    expect(leftoverMapListCriterionBadge("sales-lead", 0.5, -0.02)).not.toBeNull();
    expect(formatLeftoverMapCoordinates(null, 0.1, 0.5, -0.02)).toBeNull();
    expect(formatLeftoverMapCoordinates(Number.NaN, 0.1, 0.5, -0.02)).toBeNull();
    expect(leftoverMapListPostBadge("Public post", null, 0.1)).toBeNull();
  });

  it("stays distinct from leftover-map graphic leftover-map criterion markers, leftover-map comparison graphic leftover-map criterion markers, and leftover-map pair leftover-map post leftover-map person coordinates", () => {
    expect(LEFTOVER_MAP_LIST_CRITERION).toBe(
      "leftover pair leftover-map criterion {label} at ζ {item}",
    );
    expect(LEFTOVER_MAP_LIST_CRITERION).not.toBe(LEFTOVER_MAP_PLOT_CRITERION);
    expect(LEFTOVER_MAP_LIST_CRITERION).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_CRITERION);
    expect(LEFTOVER_MAP_LIST_CRITERION).not.toBe(LEFTOVER_MAP_LIST_POST_ACTION);
    expect(LEFTOVER_MAP_LIST_CRITERION).not.toBe("Criterion ζ {label}");
    expect(leftoverMapListCriterionBadge("sales-lead", 0.5, -0.02)?.key).not.toBe(
      leftoverMapPlotCriterionBadge("sales-lead", 0.5, -0.02)?.key ?? "",
    );
    expect(leftoverMapListCriterionBadge("sales-lead", 0.5, -0.02)?.key).not.toBe(
      leftoverMapComparePlotCriterionBadge("sales-lead", 0.5, -0.02)?.key ?? "",
    );
    expect(leftoverMapListCriterionBadge("sales-lead", 0.5, -0.02)?.key).not.toBe(
      leftoverMapListPostBadge("Public post", 0.5, 0.1)?.key ?? "",
    );
    expect(leftoverMapListCriterionBadge("sales-lead", 0.5, -0.02)?.key).not.toBe(
      leftoverMapCompareListCriterionBadge("sales-lead", 0.5, -0.02)?.key ?? "",
    );
  });
});

describe("leftoverMapCompareListPostBadge", () => {
  it("names persisted leftover-map person coordinates without inventing a leftover score", () => {
    expect(leftoverMapCompareListPostBadge("Public post", 0.5, 0.1)).toEqual({
      key: LEFTOVER_MAP_COMPARE_LIST_POST_ACTION,
      values: { title: "Public post", person: "(+0.50, +0.10)" },
    });
    expect(leftoverMapCompareListPostBadge("negative", -0.7, -0.4)).toEqual({
      key: LEFTOVER_MAP_COMPARE_LIST_POST_ACTION,
      values: { title: "negative", person: "(\u22120.70, \u22120.40)" },
    });
  });

  it("names rank-0 origin leftover-map person coordinates as ξ (0.00, 0.00)", () => {
    expect(leftoverMapCompareListPostBadge("Public post", 0, 0)).toEqual({
      key: LEFTOVER_MAP_COMPARE_LIST_POST_ACTION,
      values: { title: "Public post", person: "(0.00, 0.00)" },
    });
  });

  it("omits leftover-map person coordinates when ξ is missing or non-finite", () => {
    expect(leftoverMapCompareListPostBadge("Public post", null, 0.1)).toBeNull();
    expect(leftoverMapCompareListPostBadge("Public post", 0.5, undefined)).toBeNull();
    expect(leftoverMapCompareListPostBadge("Public post", Number.NaN, 0.1)).toBeNull();
    expect(leftoverMapCompareListPostBadge("Public post", 0.5, Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("names leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates independently of leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinates", () => {
    expect(leftoverMapCompareListPostBadge("Public post", 0.5, 0.1)).not.toBeNull();
    expect(formatLeftoverMapCoordinates(0.5, 0.1, null, -0.02)).toBeNull();
    expect(formatLeftoverMapCoordinates(0.5, 0.1, 0.5, Number.NaN)).toBeNull();
    expect(leftoverMapListCriterionBadge("sales-lead", 0.5, -0.02)).not.toBeNull();
    expect(leftoverMapCompareListCriterionBadge("sales-lead", 0.5, -0.02)).not.toBeNull();
  });

  it("stays distinct from leftover-map pair leftover-map post leftover-map person coordinates, leftover-map graphic leftover-map post markers, and leftover-map comparison graphic leftover-map post markers", () => {
    expect(LEFTOVER_MAP_COMPARE_LIST_POST_ACTION).toBe(
      "leftover map comparison leftover pair leftover-map post {title} at ξ {person}",
    );
    expect(LEFTOVER_MAP_COMPARE_LIST_POST_ACTION).not.toBe(LEFTOVER_MAP_LIST_POST_ACTION);
    expect(LEFTOVER_MAP_COMPARE_LIST_POST_ACTION).not.toBe(LEFTOVER_MAP_PLOT_POST_ACTION);
    expect(LEFTOVER_MAP_COMPARE_LIST_POST_ACTION).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_POST_ACTION);
    expect(leftoverMapCompareListPostBadge("Public post", 0.5, 0.1)?.key).not.toBe(
      leftoverMapListPostBadge("Public post", 0.5, 0.1)?.key ?? "",
    );
    expect(leftoverMapCompareListPostBadge("Public post", 0.5, 0.1)?.key).not.toBe(
      leftoverMapPlotPostBadge("Public post", 0.5, 0.1)?.key ?? "",
    );
    expect(leftoverMapCompareListPostBadge("Public post", 0.5, 0.1)?.key).not.toBe(
      leftoverMapComparePlotPostBadge("Public post", 0.5, 0.1)?.key ?? "",
    );
    expect(leftoverMapCompareListPostBadge("Public post", 0.5, 0.1)?.key).not.toBe(
      leftoverMapCompareListCriterionBadge("sales-lead", 0.5, -0.02)?.key ?? "",
    );
  });
});

describe("leftoverMapCompareListCriterionBadge", () => {
  it("names persisted leftover-map item coordinates without inventing a leftover score", () => {
    expect(leftoverMapCompareListCriterionBadge("sales-lead", 0.5, -0.02)).toEqual({
      key: LEFTOVER_MAP_COMPARE_LIST_CRITERION,
      values: { label: "sales-lead", item: "(+0.50, \u22120.02)" },
    });
    expect(leftoverMapCompareListCriterionBadge("negative", -0.7, -0.4)).toEqual({
      key: LEFTOVER_MAP_COMPARE_LIST_CRITERION,
      values: { label: "negative", item: "(\u22120.70, \u22120.40)" },
    });
  });

  it("names rank-0 origin leftover-map item coordinates as ζ (0.00, 0.00)", () => {
    expect(leftoverMapCompareListCriterionBadge("sales-lead", 0, 0)).toEqual({
      key: LEFTOVER_MAP_COMPARE_LIST_CRITERION,
      values: { label: "sales-lead", item: "(0.00, 0.00)" },
    });
  });

  it("omits leftover-map item coordinates when ζ is missing or non-finite", () => {
    expect(leftoverMapCompareListCriterionBadge("sales-lead", null, -0.02)).toBeNull();
    expect(leftoverMapCompareListCriterionBadge("sales-lead", 0.5, undefined)).toBeNull();
    expect(leftoverMapCompareListCriterionBadge("sales-lead", Number.NaN, -0.02)).toBeNull();
    expect(leftoverMapCompareListCriterionBadge("sales-lead", 0.5, Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("names leftover-map comparison leftover-pair leftover-map criterion leftover-map item coordinates independently of leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates", () => {
    expect(leftoverMapCompareListCriterionBadge("sales-lead", 0.5, -0.02)).not.toBeNull();
    expect(formatLeftoverMapCoordinates(null, 0.1, 0.5, -0.02)).toBeNull();
    expect(formatLeftoverMapCoordinates(Number.NaN, 0.1, 0.5, -0.02)).toBeNull();
    expect(leftoverMapCompareListPostBadge("Public post", null, 0.1)).toBeNull();
  });

  it("stays distinct from leftover-map pair leftover-map criterion leftover-map item coordinates, leftover-map graphic leftover-map criterion markers, leftover-map comparison graphic leftover-map criterion markers, and leftover-map comparison leftover-pair leftover-map post leftover-map person coordinates", () => {
    expect(LEFTOVER_MAP_COMPARE_LIST_CRITERION).toBe(
      "leftover map comparison leftover pair leftover-map criterion {label} at ζ {item}",
    );
    expect(LEFTOVER_MAP_COMPARE_LIST_CRITERION).not.toBe(LEFTOVER_MAP_LIST_CRITERION);
    expect(LEFTOVER_MAP_COMPARE_LIST_CRITERION).not.toBe(LEFTOVER_MAP_PLOT_CRITERION);
    expect(LEFTOVER_MAP_COMPARE_LIST_CRITERION).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_CRITERION);
    expect(LEFTOVER_MAP_COMPARE_LIST_CRITERION).not.toBe(LEFTOVER_MAP_COMPARE_LIST_POST_ACTION);
    expect(leftoverMapCompareListCriterionBadge("sales-lead", 0.5, -0.02)?.key).not.toBe(
      leftoverMapListCriterionBadge("sales-lead", 0.5, -0.02)?.key ?? "",
    );
    expect(leftoverMapCompareListCriterionBadge("sales-lead", 0.5, -0.02)?.key).not.toBe(
      leftoverMapPlotCriterionBadge("sales-lead", 0.5, -0.02)?.key ?? "",
    );
    expect(leftoverMapCompareListCriterionBadge("sales-lead", 0.5, -0.02)?.key).not.toBe(
      leftoverMapComparePlotCriterionBadge("sales-lead", 0.5, -0.02)?.key ?? "",
    );
    expect(leftoverMapCompareListCriterionBadge("sales-lead", 0.5, -0.02)?.key).not.toBe(
      leftoverMapCompareListPostBadge("Public post", 0.5, 0.1)?.key ?? "",
    );
  });
});
