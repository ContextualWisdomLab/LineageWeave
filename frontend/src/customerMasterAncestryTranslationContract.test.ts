import { describe, expect, it } from "vitest";

import { CUSTOMER_MASTER_TRANSLATION_KEYS, setCustomerMasterTranslations } from "./i18n";

const ANCESTRY_SCREEN_KEYS = [
  "Shown as top level: listed parent forms a cycle.",
  "Shown as top level: entity lists itself as parent.",
  "Shown as top level: listed parent is not visible.",
] as const;

describe("Customer Master ancestry translation contract", () => {
  it("requires every malformed-hierarchy message in the authenticated screen projection", () => {
    for (const key of ANCESTRY_SCREEN_KEYS) {
      expect(CUSTOMER_MASTER_TRANSLATION_KEYS).toContain(key);
    }
  });

  it("rejects a nominally complete projection when one ancestry message is missing", () => {
    const translations = Object.fromEntries(
      [...CUSTOMER_MASTER_TRANSLATION_KEYS, ...ANCESTRY_SCREEN_KEYS].map((key) => [key, `published:${key}`]),
    );
    delete translations[ANCESTRY_SCREEN_KEYS[0]];

    expect(() => setCustomerMasterTranslations(translations)).toThrow(
      "Incomplete Customer Master translation",
    );
  });
});
