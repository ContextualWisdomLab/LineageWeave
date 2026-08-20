import { describe, expect, it } from "vitest";
import { analysisRunTargetClock } from "./analysisRunNavigation";

describe("analysisRunTargetClock", () => {
  const context = {
    knowledgeCutoff: "2026-01-15T12:00:00Z",
    visiblePosts: [
      { post_id: "unchanged", live_after_cutoff: false },
      { post_id: "rewritten", live_after_cutoff: true },
    ],
  };

  it("uses the selected DAG target's own live_after_cutoff value", () => {
    expect(analysisRunTargetClock(context, "rewritten")).toEqual({
      liveAfterCutoff: true,
      knowledgeCutoff: context.knowledgeCutoff,
    });
    expect(analysisRunTargetClock(context, "unchanged")).toEqual({
      liveAfterCutoff: false,
      knowledgeCutoff: context.knowledgeCutoff,
    });
  });

  it("keeps the run cutoff and fails closed for a target absent from visible_posts", () => {
    expect(analysisRunTargetClock(context, "missing")).toEqual({
      liveAfterCutoff: false,
      knowledgeCutoff: context.knowledgeCutoff,
    });
  });
});
