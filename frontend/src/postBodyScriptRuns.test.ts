import { describe, expect, it } from "vitest";

import { splitScriptRuns } from "./postBodyDisplay";

describe("post body script-run grouping", () => {
  it("keeps adjacent unicode superscript and subscript digits in one semantic run", () => {
    expect(splitScriptRuns("m¹²³ and H₂₃")).toEqual([
      { text: "m" },
      { text: "123", script: "super" },
      { text: " and H" },
      { text: "23", script: "sub" },
    ]);
  });
});
