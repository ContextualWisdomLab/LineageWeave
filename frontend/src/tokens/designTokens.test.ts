import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const tokenDir = dirname(fileURLToPath(import.meta.url));

type TokenLeaf = {
  $type: string;
  $value: string;
  $description?: string;
};

function isTokenLeaf(value: unknown): value is TokenLeaf {
  if (value === null || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return typeof record.$type === "string" && typeof record.$value === "string";
}

function walkTokens(node: unknown, prefix: string[]): Array<{ path: string; token: TokenLeaf }> {
  if (isTokenLeaf(node)) {
    return [{ path: prefix.join("."), token: node }];
  }
  if (node === null || typeof node !== "object") {
    return [];
  }
  const leaves: Array<{ path: string; token: TokenLeaf }> = [];
  for (const [key, child] of Object.entries(node as Record<string, unknown>)) {
    if (key.startsWith("$")) {
      continue;
    }
    leaves.push(...walkTokens(child, [...prefix, key]));
  }
  return leaves;
}

describe("design tokens", () => {
  it("keeps every token on a two-segment path and maps it to CSS", () => {
    const catalog = JSON.parse(readFileSync(join(tokenDir, "design-tokens.json"), "utf8")) as Record<
      string,
      unknown
    >;
    const css = readFileSync(join(tokenDir, "tokens.css"), "utf8");
    const leaves = walkTokens(catalog, []);
    expect(leaves.length).toBeGreaterThan(0);
    for (const { path, token } of leaves) {
      const segments = path.split(".");
      expect(segments.length).toBeGreaterThanOrEqual(2);
      expect(token.$value.trim()).not.toBe("");
      const cssName = `--${segments.join("-")}`;
      expect(css).toContain(`${cssName}:`);
    }
  });
});
