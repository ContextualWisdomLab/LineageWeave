import { describe, expect, it } from "vitest";
import { safeHttpUrl } from "./safeHttpUrl";

describe("safeHttpUrl", () => {
  it("allows absolute HTTP(S) URLs and rejects unsafe or relative values", () => {
    expect(safeHttpUrl("https://example.test/evidence")).toBe("https://example.test/evidence");
    expect(safeHttpUrl("http://example.test/evidence")).toBe("http://example.test/evidence");
    expect(safeHttpUrl("javascript:alert(1)")).toBeNull();
    expect(safeHttpUrl("/relative/evidence")).toBeNull();
    expect(safeHttpUrl(null)).toBeNull();
  });
});
