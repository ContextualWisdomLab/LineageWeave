import { afterEach, describe, expect, it } from "vitest";

import { setLocale } from "./i18n";
import { occupationalConstructFormat } from "./occupationalConstructI18n";

describe("occupationalConstructFormat missing-placeholder coverage", () => {
  afterEach(() => {
    setLocale("en");
  });

  it("fails closed to empty copy when a named placeholder has no supplied value", () => {
    setLocale("en");

    expect(
      occupationalConstructFormat("Open supporting record: {label} · {title}", {
        label: "Skill",
      }),
    ).toBe("Open supporting record: Skill · ");
  });
});
