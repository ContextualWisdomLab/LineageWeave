/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const packageJson = JSON.parse(readFileSync(join(here, "..", "package.json"), "utf-8")) as {
  devDependencies?: Record<string, string>;
};
const storybookPreview = readFileSync(join(here, "..", ".storybook", "preview.ts"), "utf-8");
const ontologyStories = readFileSync(
  join(here, "components", "OntologyExplorer.stories.tsx"),
  "utf-8",
);

describe("Storybook viewport contract", () => {
  it("uses Storybook 10's built-in viewport module for the ontology narrow view", () => {
    expect(ontologyStories).toContain('value: "mobile1"');
    expect(packageJson.devDependencies?.storybook).toBe("^10.5.8");
    expect(packageJson.devDependencies?.["@storybook/addon-viewport"]).toBeUndefined();
    expect(storybookPreview).toContain('import { MINIMAL_VIEWPORTS } from "storybook/viewport";');
    expect(storybookPreview).toContain("options: MINIMAL_VIEWPORTS");
  });
});
