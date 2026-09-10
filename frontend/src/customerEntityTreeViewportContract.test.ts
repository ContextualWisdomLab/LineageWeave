/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const stories = readFileSync(join(here, "CustomerEntityTreeRow.stories.tsx"), "utf-8");

describe("Customer Master Storybook viewport contract", () => {
  it("pins malformed-hierarchy responsive stories with Storybook 10 viewport globals", () => {
    expect(stories).toContain('globals: { viewport: { value: "mobile1", isRotated: false } }');
    expect(stories).toContain('globals: { viewport: { value: "tablet", isRotated: false } }');
    expect(stories).not.toContain("parameters: { viewport: { defaultViewport:");
  });
});
