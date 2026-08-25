import { describe, expect, it } from "vitest";
import { focusedGraphMustReset } from "./focusedGraphSelection";

describe("focusedGraphMustReset", () => {
  it("retains a loaded graph when the already-open post is selected again", () => {
    expect(focusedGraphMustReset("post-1", "post-1")).toBe(false);
    expect(focusedGraphMustReset("post-1", "post-2")).toBe(true);
  });
});
