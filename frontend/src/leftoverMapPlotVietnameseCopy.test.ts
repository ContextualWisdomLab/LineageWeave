import { afterEach, describe, expect, it } from "vitest";
import { setLocale, tf } from "./i18n";

const GRAPHIC_DISPLAY_COPY =
  "Leftover map after IRT main effects. Axis ticks name persisted leftover-map coordinates. Pair segments name leftover-map distance d, leftover-map reconstruction R̂, leftover-map explained leftover share e, leftover-map unexplained leftover share s, leftover-map cross share x, leftover-map unexplained leftover U, leftover residual R, leftover observed Y, leftover expected E, and leftover-map rank. Click a post marker to open that post. The plot does not invent a leftover score.";

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

    expect(tf(GRAPHIC_DISPLAY_COPY, {})).toContain(
      "tỷ phần phần dư được giải thích e",
    );
  });
});
