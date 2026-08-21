import { afterEach, describe, expect, it } from "vitest";
import { setLocale } from "./i18n";
import { ontologyExplorerText } from "./ontologyExplorerI18n";

const KEYS = [
  "Load next relation page",
  "Neighborhood truncated. Load the next relation page or inspect one edge.",
  "No direct evidence post is attached. Review the provenance reference above.",
] as const;

afterEach(() => {
  setLocale("en");
});

describe("ontologyExplorerText", () => {
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
