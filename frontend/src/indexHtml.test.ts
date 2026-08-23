/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const indexHtml = readFileSync(join(here, "..", "index.html"), "utf-8");

describe("index.html no-JS fallback", () => {
  it("shows real visible content inside <noscript>, not an empty tag", () => {
    const match = indexHtml.match(/<noscript>([\s\S]*?)<\/noscript>/);
    expect(match).not.toBeNull();
    const noscriptBody = match?.[1] ?? "";
    expect(noscriptBody.replace(/<[^>]+>/g, "").trim().length).toBeGreaterThan(0);
    expect(noscriptBody).toContain("requires JavaScript");
  });

  it("places the noscript fallback before the JS entry point loads", () => {
    const noscriptIndex = indexHtml.indexOf("<noscript>");
    const scriptIndex = indexHtml.indexOf('<script type="module"');
    expect(noscriptIndex).toBeGreaterThan(-1);
    expect(noscriptIndex).toBeLessThan(scriptIndex);
  });
});
