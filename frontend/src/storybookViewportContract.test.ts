/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const packageJson = JSON.parse(readFileSync(join(here, "..", "package.json"), "utf-8")) as {
  devDependencies?: Record<string, string>;
};
const storybookMain = readFileSync(join(here, "..", ".storybook", "main.ts"), "utf-8");
const ontologyStories = readFileSync(
  join(here, "components", "OntologyExplorer.stories.tsx"),
  "utf-8",
);

describe("Storybook viewport contract", () => {
  it("registers the viewport addon used by the ontology narrow-view story", () => {
    expect(ontologyStories).toContain('value: "mobile1"');
    expect(packageJson.devDependencies?.["@storybook/addon-viewport"]).toBe("^10.5.8");
    expect(storybookMain).toContain('addons: ["@storybook/addon-viewport"]');
  });
});
