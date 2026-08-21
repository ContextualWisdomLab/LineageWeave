import { afterEach, describe, expect, it } from "vitest";
import { setLocale } from "./i18n";
import { lineageDagText } from "./lineageDagI18n";

afterEach(() => {
  setLocale("en");
});

describe("lineageDagText", () => {
  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates the lineage meaning boundary in %s",
    (locale) => {
      setLocale(locale);
      expect(lineageDagText("Lineage legend")).not.toBe("Lineage legend");
      expect(lineageDagText("Root record")).not.toBe("Root record");
      expect(lineageDagText("Branch point")).not.toBe("Branch point");
      expect(lineageDagText("Current record")).not.toBe("Current record");
      expect(lineageDagText("Parent to child")).not.toBe("Parent to child");
      expect(
        lineageDagText(
          "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.",
        ),
      ).not.toBe(
        "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.",
      );
    },
  );
});
