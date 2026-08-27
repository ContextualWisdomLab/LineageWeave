import { afterEach, describe, expect, it } from "vitest";
import { ANALYSIS_RUN_COPY_KEYS, analysisRunText } from "./analysisRunI18n";
import { setLocale } from "./i18n";

afterEach(() => setLocale("en"));

describe("analysis-run guidance localization", () => {
  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates every next-action and corpus state in %s",
    (locale) => {
      setLocale("en");
      const english = new Map(
        ANALYSIS_RUN_COPY_KEYS.map((key) => [key, analysisRunText(key)]),
      );
      setLocale(locale);
      for (const key of ANALYSIS_RUN_COPY_KEYS) {
        expect(analysisRunText(key), `${locale}:${key}`).not.toBe(english.get(key));
      }
    },
  );
});
