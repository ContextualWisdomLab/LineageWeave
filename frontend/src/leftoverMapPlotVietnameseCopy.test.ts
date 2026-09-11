import { afterEach, describe, expect, it } from "vitest";
import { setLocale, tf } from "./i18n";
import {
  LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPLAINED_SHARE,
  LEFTOVER_MAP_PLOT_CAPTION,
} from "./leftoverMapPlotLayout";

afterEach(() => {
  setLocale("en");
});

describe("leftover-map Vietnamese copy inheritance", () => {
  it("keeps explained leftover share terminology as an explicit share", () => {
    setLocale("vi");

    expect(
      tf("leftover-map explained leftover share {label}", { label: "R̂²/R² 0.76" }),
    ).toBe("tỷ phần phần dư được giải thích trên bản đồ phần dư R̂²/R² 0.76");
  });

  it("keeps the expanded graphic description explicit about explained share e", () => {
    setLocale("vi");

    const caption = tf(LEFTOVER_MAP_PLOT_CAPTION, {});
    expect(caption).toContain("tỷ phần phần dư được giải thích e");
    expect(caption).not.toContain("phần dư giải thích e");
  });

  it("keeps comparison graphic explained share terminology explicit", () => {
    setLocale("vi");

    expect(
      tf(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPLAINED_SHARE, {
        label: "R̂²/R² 0.76",
      }),
    ).toBe(
      "tỷ phần phần dư được giải thích trên đồ họa so sánh bản đồ phần dư R̂²/R² 0.76",
    );
  });
});
