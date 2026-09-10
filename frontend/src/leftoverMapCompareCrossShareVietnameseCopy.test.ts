import { afterEach, describe, expect, it } from "vitest";
import { setLocale, tf } from "./i18n";

afterEach(() => {
  setLocale("en");
});

describe("leftover-map comparison Vietnamese cross-share copy", () => {
  it("preserves share meaning in the production graphic accessible name", () => {
    setLocale("vi");
    expect(
      tf("leftover map comparison graphic cross share {label}", {
        label: "2R̂U/R² 0.12",
      }),
    ).toBe(
      "tỷ phần giao trên đồ họa so sánh bản đồ phần dư 2R̂U/R² 0.12",
    );
  });
});
