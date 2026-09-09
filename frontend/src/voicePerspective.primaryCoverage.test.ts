import { describe, expect, it } from "vitest";
import { postPrimaryVoiceLabel } from "./voicePerspective";

describe("postPrimaryVoiceLabel governed primary assignment", () => {
  it("prefers the governed primary Voice label over legacy VOC fields", () => {
    expect(
      postPrimaryVoiceLabel({
        voc_type_code: "legacy-voc",
        voc_type_label: "Legacy VOC label",
        voice_types: [
          {
            code: "vops",
            label: "Voice of Process",
            is_primary: false,
            truth_status_code: "truth_observed",
            evidence_available: true,
          },
          {
            code: "voc",
            label: "Governed Voice of Customer",
            is_primary: true,
            truth_status_code: "truth_observed",
            evidence_available: true,
          },
        ],
      }),
    ).toBe("Governed Voice of Customer");
  });
});
