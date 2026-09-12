import { afterEach, describe, expect, it } from "vitest";
import { setLocale, t, tf, type Locale } from "./i18n";
import {
  LEFTOVER_MAP_COMPARE_PLOT_LABEL,
  LEFTOVER_MAP_PLOT_SEGMENT_RANK,
} from "./leftoverMapPlotLayout";

const EXPECTED = [
  ["ko", "잔여 지도 비교 그림: 잔여 지도 순위 rank 1"],
  ["zh", "残差地图比较图形: 残差图秩 rank 1"],
  ["ja", "残差マップの比較図: 残差マップ階数 rank 1"],
  ["vi", "Đồ họa so sánh bản đồ phần dư: hạng bản đồ phần dư rank 1"],
] as const satisfies readonly (readonly [Exclude<Locale, "en">, string])[];

function comparisonRankAccessibleName(label: string): string {
  return `${t(LEFTOVER_MAP_COMPARE_PLOT_LABEL)}: ${tf(LEFTOVER_MAP_PLOT_SEGMENT_RANK, { label })}`;
}

afterEach(() => {
  setLocale("en");
});

describe("grouping-comparison leftover-map rank localization", () => {
  it.each(EXPECTED)("keeps the accessible rank caption localized in %s", (locale, expected) => {
    setLocale(locale);
    expect(comparisonRankAccessibleName("rank 1")).toBe(expected);
  });
});
