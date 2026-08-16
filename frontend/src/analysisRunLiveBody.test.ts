import { describe, expect, it } from "vitest";
import { analysisRunLiveBodyComparison } from "./analysisRunLiveBody";

describe("analysisRunLiveBodyComparison", () => {
  it("tells the operator not to treat a post-cutoff rewrite as evidence", () => {
    expect(
      analysisRunLiveBodyComparison("2026-01-12T12:00:00Z", "2026-02-01T00:00:00Z"),
    ).toBe(
      "This live body was last written after cutoff 2026-01-12. Do not treat it as reconstructed evidence.",
    );
  });

  it("confirms a write clock that is still inside the cutoff", () => {
    expect(
      analysisRunLiveBodyComparison("2026-01-12T12:00:00Z", "2026-01-10T12:00:00Z"),
    ).toBe(
      "This live body has not been written since cutoff 2026-01-12. You can treat the opened text as the cutoff corpus for this run.",
    );
  });
});
