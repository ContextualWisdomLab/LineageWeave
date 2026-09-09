import { describe, expect, it } from "vitest";
import { splitPostBody } from "./postBodyDisplay";

describe("exported CSS indentation", () => {
  it("does not invent hierarchy from malformed or non-positive indentation", () => {
    expect(
      splitPostBody(
        '<p style="margin-left: nonsense">Malformed</p>' +
          '<p style="margin-left: -16px">Negative</p>' +
          '<p style="margin-left: 0">Zero</p>',
      ),
    ).toEqual([
      { kind: "text", text: "Malformed" },
      { kind: "text", text: "Negative" },
      { kind: "text", text: "Zero" },
    ]);
  });

  it("uses the physical left value from one-, two-, and four-value margin shorthands", () => {
    expect(
      splitPostBody(
        '<p style="margin: 8px">One</p>' +
          '<p style="margin: 0 16px">Two</p>' +
          '<p style="margin: 0 0 0 24px">Three</p>',
      ),
    ).toEqual([
      { kind: "text", text: "One", indentLevel: 1 },
      { kind: "text", text: "Two", indentLevel: 2 },
      { kind: "text", text: "Three", indentLevel: 3 },
    ]);
  });
});
