import { afterEach, describe, expect, it } from "vitest";
import { setLocale, tf, type Locale } from "./i18n";

const RANK_KEY = "leftover map comparison graphic leftover-map rank {label}";

const EXPECTED = [
  ["ko", "잔여 지도 비교 그림 순위 rank 1"],
  ["zh", "残差地图比较图形秩 rank 1"],
  ["ja", "残差マップの比較図階数 rank 1"],
  ["vi", "hạng đồ họa so sánh bản đồ phần dư rank 1"],
] as const satisfies readonly (readonly [Exclude<Locale, "en">, string])[];

afterEach(() => {
  setLocale("en");
});

describe("grouping-comparison leftover-map rank localization", () => {
  it.each(EXPECTED)("keeps the accessible rank caption localized in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf(RANK_KEY, { label: "rank 1" })).toBe(expected);
  });
});
