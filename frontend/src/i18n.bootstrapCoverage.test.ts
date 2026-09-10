import { afterEach, describe, expect, it, vi } from "vitest";

const STORAGE_KEY = "lineageweave.locale";

async function reloadI18n() {
  vi.resetModules();
  return import("./i18n");
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.removeItem(STORAGE_KEY);
  document.documentElement.lang = "en";
  vi.resetModules();
});

describe("i18n browser bootstrap", () => {
  it("restores a persisted supported locale on a later browser visit", async () => {
    window.localStorage.setItem(STORAGE_KEY, "ja");

    const i18n = await reloadI18n();

    expect(i18n.getLocale()).toBe("ja");
    expect(document.documentElement.lang).toBe("ja");
  });

  it("falls back to English when the browser locale has no product resource", async () => {
    window.localStorage.removeItem(STORAGE_KEY);
    vi.stubGlobal("navigator", { language: "pt-BR" });

    const i18n = await reloadI18n();

    expect(i18n.getLocale()).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });

  it("does not require navigator during non-browser bootstrap", async () => {
    window.localStorage.removeItem(STORAGE_KEY);
    vi.stubGlobal("navigator", undefined);

    const i18n = await reloadI18n();

    expect(i18n.getLocale()).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });
});
