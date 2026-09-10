/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const appSource = readFileSync(join(here, "App.tsx"), "utf8");

describe("grouping comparison axis-share accessibility", () => {
  it("keeps persisted axis-share text visible without naming a generic span", () => {
    const marker = "const comparisonAxisShare = leftoverMapCompareAxisShare(axis);";
    expect(appSource).toContain(marker);
    const shareBlock = appSource.split(marker, 2)[1]?.split("{row.leftover_pairs", 1)[0] ?? "";

    expect(shareBlock).toContain('className="post-badge"');
    expect(shareBlock).toContain("LEFTOVER_MAP_COMPARE_AXIS_SHARE, comparisonAxisShare");
    expect(shareBlock).not.toContain("aria-label=");
  });
});