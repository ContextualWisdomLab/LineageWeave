import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, it } from "vitest";

const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "App.css"), "utf-8");

it("keeps the workspace GNB reachable on mobile", () => {
  const mobile = css.match(/@media \(max-width: 768px\) \{([\s\S]*?)\n\}/)?.[1] ?? "";
  expect(mobile).toContain(".workspace-gnb");
  expect(mobile).toContain("overflow-x: auto");
  expect(mobile).not.toContain(".workspace-gnb {\n    display: none");
});
