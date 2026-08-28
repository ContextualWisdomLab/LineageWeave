import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, it } from "vitest";

const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "App.css"), "utf-8");

it("keeps the workspace GNB reachable on mobile", () => {
  const mobileBlocks = [...css.matchAll(/@media \(max-width: 768px\) \{([\s\S]*?)\n\}/g)]
    .map((match) => match[1] ?? "");
  expect(mobileBlocks.some((block) => (
    block.includes(".workspace-gnb") && block.includes("overflow-x: auto")
  ))).toBe(true);
  expect(mobileBlocks.join("\n")).not.toContain(".workspace-gnb {\n    display: none");
});
