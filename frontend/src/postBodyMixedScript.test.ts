import { describe, expect, it } from "vitest";

import { normalizeScriptText, splitScriptRuns } from "./postBodyDisplay";

describe("mixed-script caret exponent boundary", () => {
  it.each(["x^123٤", "x^123.٤", "x^{١}", "x^{12٤}"])(
    "keeps the complete unsupported token literal: %s",
    (text) => {
      expect(normalizeScriptText(text)).toBe(text);
      expect(splitScriptRuns(text)).toEqual([{ text }]);
    },
  );
});
