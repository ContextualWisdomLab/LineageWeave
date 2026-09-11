import { afterEach, describe, expect, it } from "vitest";
import { getLocale, setLocale, SUPPORTED_LOCALES } from "./i18n";
import { ontologyExplorerText } from "./ontologyExplorerI18n";

afterEach(() => {
  setLocale("en");
});

describe("global locale admission", () => {
  it("does not admit a globally selectable locale that silently falls back to English", () => {
    const englishCopy = "Load next relation page";

    for (const locale of SUPPORTED_LOCALES) {
      setLocale(locale);
      expect(getLocale()).toBe(locale);

      if (locale !== "en") {
        expect(
          ontologyExplorerText("Load next relation page"),
          `${locale} is globally selectable but Ontology Explorer falls back to English`,
        ).not.toBe(englishCopy);
      }
    }
  });
});
