import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const appSource = readFileSync(fileURLToPath(new URL("./App.tsx", import.meta.url)), "utf8");

describe("grouping comparison axis-share accessibility", () => {
  it("keeps persisted axis-share text visible without naming a generic span", () => {
    const marker = "{comparisonAxisShare !== null ? (";
    expect(appSource).toContain(marker);
    const shareBlock = appSource.split(marker, 2)[1]?.split(") : null}", 1)[0] ?? "";

    expect(shareBlock).toContain('className="post-badge"');
    expect(shareBlock).toContain("LEFTOVER_MAP_COMPARE_AXIS_SHARE, comparisonAxisShare");
    expect(shareBlock).not.toContain("aria-label=");
  });
});
