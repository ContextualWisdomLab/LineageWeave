import { describe, expect, it } from "vitest";
import { splitPostBody } from "./postBodyDisplay";

describe("splitPostBody quoted boundary attributes", () => {
  it("does not leak a quoted greater-than attribute from a paragraph tag into buyer-visible text", () => {
    expect(splitPostBody('<p title="a > b">First</p><p>Second</p>')).toEqual([
      { kind: "text", text: "First" },
      { kind: "text", text: "Second" },
    ]);
  });

  it("preserves a line break whose quoted attribute contains a greater-than sign", () => {
    expect(splitPostBody('<p>First<br title="a > b">Second</p>')).toEqual([
      { kind: "text", text: "First" },
      { kind: "text", text: "Second" },
    ]);
  });
});
