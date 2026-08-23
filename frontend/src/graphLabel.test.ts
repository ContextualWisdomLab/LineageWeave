import { describe, expect, it } from "vitest";
import { wrapLabel } from "./graphLabel";

const LONG_A100_TITLE = "Initial site visit and project scope discussion";

describe("wrapLabel", () => {
  it("keeps the full A-100 fixture title without ellipsis", () => {
    const lines = wrapLabel(LONG_A100_TITLE, 26);
    expect(lines.join(" ")).toBe(LONG_A100_TITLE);
    expect(lines.some((line) => line.includes("…") || line.includes("..."))).toBe(false);
    expect(lines.length).toBeGreaterThan(1);
    expect(lines.every((line) => line.length <= 26 || !/\s/.test(line))).toBe(true);
  });

  it("keeps an over-long spaced token on its own line instead of ellipsizing", () => {
    const lines = wrapLabel("See Supercalifragilisticexpialidocious now", 12);
    expect(lines).toEqual(["See", "Supercalifragilisticexpialidocious", "now"]);
    expect(lines.join(" ")).toBe("See Supercalifragilisticexpialidocious now");
  });

  it("wraps a script without spaces by character budget and keeps every character", () => {
    const title = "초기현장방문및프로젝트범위논의";
    expect(wrapLabel(title, 8).join("")).toBe(title);
    expect(wrapLabel(title, 8).length).toBeGreaterThan(1);
  });

  it("returns the original empty-ish value rather than a placeholder", () => {
    expect(wrapLabel("   ", 26)).toEqual(["   "]);
  });
});
