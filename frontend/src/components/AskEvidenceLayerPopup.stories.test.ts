import { describe, expect, it } from "vitest";
import meta, { EventTimeAxis, IngestionTimeAxisFallback } from "./AskEvidenceLayerPopup.stories";

describe("AskEvidenceLayerPopup Storybook contract", () => {
  it("exports CSF metadata for the event-time evidence states", () => {
    expect(meta.title).toBe("Evidence/AskEvidenceLayerPopup");
    expect(meta.component).toBeDefined();
    expect(EventTimeAxis.args?.facts).toEqual([
      { kind: "time_axis", text: "time axis: event occurred at" },
    ]);
    expect(IngestionTimeAxisFallback.args?.facts).toEqual([
      { kind: "time_axis", text: "time axis: record created at" },
    ]);
  });
});
