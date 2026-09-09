import { describe, expect, it } from "vitest";
import { chatEvidenceKindLabel } from "./evidenceKindLabels";

describe("chatEvidenceKindLabel", () => {
  it("uses the cataloged kind label and keeps unknown kinds as Evidence", () => {
    expect(chatEvidenceKindLabel("time_axis")).toBe("Time axis");
    expect(chatEvidenceKindLabel("semantic_project")).toBe("Semantic project");
    expect(chatEvidenceKindLabel("unlisted-kind")).toBe("Evidence");
  });
});
