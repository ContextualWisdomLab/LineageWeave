import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, it } from "vitest";

const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "App.css"), "utf-8");

it("keeps the workspace GNB reachable on mobile", () => {
  const mobile = css.match(/@media \(max-width: 768px\) \{([\s\S]*?)\n\}/)?.[1] ?? "";
  expect(mobile).toContain(".workspace-gnb");
  expect(mobile).toContain("grid-template-columns: repeat(3, minmax(0, 1fr))");
  expect(mobile).toContain("height: auto");
  expect(mobile).toContain("grid-column: 1 / -1");
  expect(mobile).toContain("min-height: var(--size-control-min)");
  expect(mobile).not.toContain("overflow-x: auto");
  expect(mobile).not.toContain(".workspace-gnb {\n    display: none");
});
