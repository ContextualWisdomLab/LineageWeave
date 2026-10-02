import { describe, expect, it } from "vitest";
import { normalizeScriptText, splitPostBody } from "./postBodyDisplay";

describe("post body malformed-markup resilience", () => {
  it("does not recompose a removed anchor into a new tag token", () => {
    expect(splitPostBody("<<a>script>")).toEqual([
      { kind: "text", text: "< script>" },
    ]);
    expect(splitPostBody("<<a>")).toEqual([
      { kind: "text", text: "<" },
    ]);
  });

  it("does not leak footnote state from unmatched closing containers", () => {
    expect(splitPostBody("</ol><p>Ordinary body</p>")).toEqual([
      { kind: "text", text: "Ordinary body" },
    ]);
  });

  it("does not leak footnote role from a self-closing footnote container", () => {
    expect(splitPostBody('<ol class="footnotes"/><p>Ordinary body</p>')).toEqual([
      { kind: "text", text: "Ordinary body" },
    ]);
  });

  it("preserves blockquote indentation as one semantic level", () => {
    expect(splitPostBody("<blockquote>Quoted body</blockquote><p>Root body</p>")).toEqual([
      { kind: "text", text: "Quoted body", indentLevel: 1 },
      { kind: "text", text: "Root body" },
    ]);
  });

  it("keeps empty and non-numeric script markup deterministic", () => {
    expect(normalizeScriptText("<sup></sup>")).toBe("");
    expect(normalizeScriptText("<sub>abc</sub>")).toBe("_abc");
  });

  it("keeps an empty pipe row as prose instead of inventing a table", () => {
    expect(splitPostBody("|   |")).toEqual([
      { kind: "text", text: "|   |" },
    ]);
  });
});
