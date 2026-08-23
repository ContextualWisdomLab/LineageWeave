/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "App.css"), "utf-8");

describe("board CSS contract", () => {
  it("keeps one canonical control layout so responsive rows are not overridden", () => {
    expect(css).toContain(
      ".board-controls {\n  margin-bottom: 1.5rem;"
    );
    expect(css).toContain(".board-search-row");
    expect(css).toContain(
      '.board-controls input[type="search"],\n.board-controls select {\n  font: inherit;'
    );
    expect(css).not.toContain(
      "grid-template-columns: minmax(12rem, 2fr) repeat(3, minmax(8rem, 1fr)) auto;"
    );
  });
});
