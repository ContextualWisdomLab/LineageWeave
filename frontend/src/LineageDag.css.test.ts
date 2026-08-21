/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "LineageDag.css"), "utf-8");

describe("LineageDag CSS contracts", () => {
  it("keeps the event-date selector at least as specific as the shared node-text rule", () => {
    expect(css).toContain(".lineage-dag-node text.lineage-dag-node-date {");
    expect(css).not.toMatch(/(^|\n)\.lineage-dag-node-date\s*\{/);
  });
});
