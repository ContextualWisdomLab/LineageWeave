/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const appCss = readFileSync(join(here, "App.css"), "utf-8");

describe("Ontology Explorer CSS contracts", () => {
  it("defines the ontology node focus-visible rule exactly once", () => {
    expect(appCss.match(/\.ontology-node:focus-visible\s*\{/g)).toHaveLength(1);
  });

  it("lets the node-type label override the shared node text color", () => {
    expect(appCss).toContain(".ontology-node text.ontology-node-type {");
  });
});
