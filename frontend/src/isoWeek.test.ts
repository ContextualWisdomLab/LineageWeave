import { describe, expect, it } from "vitest";
import { isoWeekFromCreatedAt, latestIsoWeek } from "./isoWeek";

describe("isoWeekFromCreatedAt", () => {
  it("places Thursday 1 January 2026 in 2026-W01", () => {
    expect(isoWeekFromCreatedAt("2026-01-01T00:00:00Z")).toBe("2026-W01");
  });

  it("places Monday 5 January 2026 in 2026-W02", () => {
    expect(isoWeekFromCreatedAt("2026-01-05T00:00:00Z")).toBe("2026-W02");
  });

  it("places Monday 29 December 2025 in 2026-W01", () => {
    expect(isoWeekFromCreatedAt("2025-12-29T00:00:00Z")).toBe("2026-W01");
  });

  it("returns null for missing or unusable timestamps", () => {
    expect(isoWeekFromCreatedAt(undefined)).toBeNull();
    expect(isoWeekFromCreatedAt("not-a-date")).toBeNull();
  });
});

describe("latestIsoWeek", () => {
  it("returns the latest formatted ISO week and ignores empty values", () => {
    expect(latestIsoWeek(["2026-W01", null, "2025-W52", "2026-W03"])).toBe("2026-W03");
    expect(latestIsoWeek([null, undefined])).toBeNull();
  });
});
