import { describe, expect, it } from "vitest";
import {
  leftoverBadgeText,
  leftoverPairsForPost,
  leftoverRowLabel,
} from "./leftoverCaption";

describe("leftoverCaption", () => {
  it("names closest and farthest leftover badges without inventing a theta", () => {
    expect(leftoverRowLabel("closest")).toBe("Closest leftover");
    expect(leftoverRowLabel("farthest")).toBe("Farthest leftover");
    expect(
      leftoverBadgeText({
        pair_kind: "closest",
        post_id: "post-1",
        post_title: "Public post",
        criterion_code: "sales_lead_specificity",
        leftover_distance: 0.12,
        leftover_residual: 0.4,
      }),
    ).toBe("Closest leftover · sales-lead");
  });

  it("keeps leftover pairs bound to the named post only", () => {
    const pairs = [
      {
        pair_kind: "closest" as const,
        post_id: "post-1",
        post_title: "Public post",
        criterion_code: "sales_lead_specificity",
        leftover_distance: 0.12,
        leftover_residual: 0.4,
      },
      {
        pair_kind: "farthest" as const,
        post_id: "post-2",
        post_title: "Linked post",
        criterion_code: "general_sentiment_negative",
        leftover_distance: 1.84,
        leftover_residual: -1.1,
      },
    ];
    expect(leftoverPairsForPost(pairs, "post-1")).toEqual([pairs[0]]);
    expect(leftoverPairsForPost(undefined, "post-1")).toEqual([]);
  });
});
