import { afterEach, describe, expect, it } from "vitest";
import { setLocale } from "./i18n";
import { lineageDagText } from "./lineageDagI18n";

afterEach(() => {
  setLocale("en");
});

describe("lineageDagText", () => {
  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates the lineage meaning and next-action boundary in %s",
    (locale) => {
      setLocale(locale);
      expect(lineageDagText("Lineage legend")).not.toBe("Lineage legend");
      expect(lineageDagText("Root record")).not.toBe("Root record");
      expect(lineageDagText("Branch point")).not.toBe("Branch point");
      expect(lineageDagText("Current record")).not.toBe("Current record");
      expect(lineageDagText("Parent to child")).not.toBe("Parent to child");
      expect(lineageDagText("Topic")).not.toBe("Topic");
      expect(lineageDagText("Predecessor to successor")).not.toBe("Predecessor to successor");
      expect(lineageDagText("Earlier")).not.toBe("Earlier");
      expect(lineageDagText("Later")).not.toBe("Later");
      expect(
        lineageDagText(
          "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.",
        ),
      ).not.toBe(
        "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.",
      );
      expect(
        lineageDagText(
          "No reconstructed lineage yet. Add eligible source records, then rebuild Event Lineage.",
        ),
      ).not.toBe(
        "No reconstructed lineage yet. Add eligible source records, then rebuild Event Lineage.",
      );
      expect(
        lineageDagText(
          "This chain has no branch point: each record matched exactly one likely predecessor. See the evidence trail below for why each link was made.",
        ),
      ).not.toBe(
        "This chain has no branch point: each record matched exactly one likely predecessor. See the evidence trail below for why each link was made.",
      );
    },
  );
});
