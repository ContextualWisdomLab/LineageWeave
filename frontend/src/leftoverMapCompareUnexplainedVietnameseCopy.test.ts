import { afterEach, describe, expect, it } from "vitest";
import { setLocale, tf } from "./i18n";
import { LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED_SHARE } from "./leftoverMapUnexplainedShare";

afterEach(() => {
  setLocale("en");
});

describe("leftover-map comparison Vietnamese unexplained-share copy", () => {
  it("preserves the share meaning in the production graphic accessible name", () => {
    setLocale("vi");
    expect(
      tf(LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_UNEXPLAINED_SHARE, {
        label: "U²/R² 0.24",
      }),
    ).toBe(
      "tỷ phần phần dư chưa giải thích trên đồ họa so sánh bản đồ phần dư U²/R² 0.24",
    );
  });
});
