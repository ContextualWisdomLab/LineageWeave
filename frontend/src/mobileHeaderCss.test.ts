/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const appCss = readFileSync(join(here, "App.css"), "utf-8");
const phoneMedia = appCss.split("@media (max-width: 768px)")[1] ?? "";

describe("mobile header CSS contract", () => {
  it("keeps one phone app-header rule with vertical padding", () => {
    expect(phoneMedia.match(/\.app-header\s*\{/g)).toHaveLength(1);
    expect(phoneMedia).toContain("padding: 0.6rem 1rem;");
    expect(phoneMedia).not.toContain("padding: 0 1rem;");
  });
});
