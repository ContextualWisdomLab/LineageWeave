import { describe, expect, it } from "vitest";
import { normalizeScriptText, splitPostBody } from "./postBodyDisplay";

describe("post-body scanner edge coverage", () => {
  it("keeps a comparison-looking less-than sequence inside script content literal", () => {
    expect(normalizeScriptText("x<sup>2 < 3</sup>")).toBe("x^2 < 3");
  });

  it("finds the matching outer close when script tags of the same kind are nested", () => {
    expect(normalizeScriptText("x<sup>2<sup>3</sup></sup>")).toBe("x²³");
  });

  it("preserves an unterminated script tag instead of consuming the remaining text", () => {
    expect(normalizeScriptText("x<sup>2")).toBe("x<sup>2");
  });

  it("fails closed for an unquoted embedded-image src without exposing the data URI", () => {
    const segments = splitPostBody("<img src=data:image/png;base64,AAAA>");

    expect(segments.every((segment) => segment.kind === "text")).toBe(true);
    expect(JSON.stringify(segments)).not.toContain("data:image/png;base64,AAAA");
  });
});
