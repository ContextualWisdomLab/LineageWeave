import { afterEach, describe, expect, it } from "vitest";
import { setLocale, t, tf, type Locale } from "./i18n";
import {
  LEFTOVER_MAP_COMPARE_PLOT_LABEL,
  LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE,
} from "./leftoverMapPlotLayout";

const PRODUCT_LOCALES = ["ko", "zh", "ja", "vi"] as const satisfies readonly Exclude<Locale, "en">[];

function comparisonDistanceAccessibleName(label: string): string {
  return `${t(LEFTOVER_MAP_COMPARE_PLOT_LABEL)}: ${tf(LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE, { label })}`;
}

afterEach(() => {
  setLocale("en");
});

describe("grouping-comparison leftover-map distance localization", () => {
  it.each(PRODUCT_LOCALES)("keeps comparison distance accessible naming localized in %s", (locale) => {
    setLocale(locale);
    const comparisonLabel = t(LEFTOVER_MAP_COMPARE_PLOT_LABEL);
    const distanceLabel = tf(LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE, { label: "d 1.25" });

    expect(comparisonLabel).not.toBe(LEFTOVER_MAP_COMPARE_PLOT_LABEL);
    expect(distanceLabel).not.toBe("leftover-map distance d 1.25");
    expect(distanceLabel).toContain("d 1.25");
    expect(comparisonDistanceAccessibleName("d 1.25")).toBe(`${comparisonLabel}: ${distanceLabel}`);
  });
});
