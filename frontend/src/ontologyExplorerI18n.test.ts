import { afterEach, describe, expect, it } from "vitest";
import { setLocale } from "./i18n";
import { ontologyExplorerText } from "./ontologyExplorerI18n";

const KEYS = [
  "Load next relation page",
  "Neighborhood truncated. Load the next relation page or inspect one edge.",
  "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.",
  "No direct evidence post is attached. Review the provenance reference above.",
  "Scroll horizontally to see all columns, including evidence and recorded time.",
] as const;

afterEach(() => {
  setLocale("en");
});

describe("ontologyExplorerText", () => {
  it("directs readers to the available continuation action", () => {
    expect(ontologyExplorerText("Neighborhood truncated. Load the next relation page or inspect one edge."))
      .toBe("Some related information is not shown. Load the next relation page.");
  });

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates paging and evidence guidance in %s",
    (locale) => {
      setLocale(locale);
      for (const key of KEYS) {
        expect(ontologyExplorerText(key)).not.toBe(key);
      }
    },
  );
});
