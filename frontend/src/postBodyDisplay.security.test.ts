import { describe, expect, it } from "vitest";
import { normalizeScriptText, splitPostBody } from "./postBodyDisplay";

describe("post body markup boundary", () => {
  it("does not synthesize an executable-looking tag when adjacent markup is removed", () => {
    const segments = splitPostBody("<<a>script>alert(1)<</a>/script>");
    const text = segments
      .filter((segment) => segment.kind === "text")
      .map((segment) => segment.text)
      .join(" ")
      .toLowerCase();

    expect(text).not.toContain("<script");
    expect(text).not.toContain("</script");
  });

  it("parses quoted greater-than characters inside nested scientific markup", () => {
    expect(normalizeScriptText('<sup><span title="a > b">2</span></sup>')).toBe("²");
  });

  it("parses quoted greater-than characters on the scientific script tag itself", () => {
    expect(normalizeScriptText('<sup title="a > b">2</sup>')).toBe("²");
    expect(normalizeScriptText('<sub data-rule="x > 0">2</sub>')).toBe("₂");
  });
});
