import { describe, expect, it } from "vitest";
import { splitPostBody } from "./postBodyDisplay";

describe("splitPostBody whitespace-only embedded image", () => {
  it("rejects an embedded image whose base64 payload becomes empty after normalization", () => {
    const segments = splitPostBody('<img src="data:image/png;base64,   ">');

    expect(segments).toEqual([
      {
        kind: "text",
        text: "Embedded image could not be decoded. Re-export the source post and open it again.",
      },
    ]);
    expect(segments.some((segment) => segment.kind === "image")).toBe(false);
  });
});
