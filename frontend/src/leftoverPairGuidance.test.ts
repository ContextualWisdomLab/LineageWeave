import { describe, expect, it } from "vitest";
import {
  leftoverCriterionLabel,
  leftoverPairAriaLabel,
  leftoverPairNextAction,
  leftoverPairOpenOptions,
  leftoverPairTitle,
  postQualityCriterionElementId,
} from "./leftoverPairGuidance";

const closest = {
  pair_kind: "closest",
  post_id: "post-1",
  post_title: "Public post",
  criterion_code: "sales_lead_specificity",
};

const farthest = {
  pair_kind: "farthest",
  post_id: "post-spec",
  post_title: "Specification revision requested",
  criterion_code: "general_sentiment_negative",
};

describe("leftoverPairGuidance", () => {
  it("names the post and the criterion in leftover next-action copy", () => {
    const closestCopy = leftoverPairNextAction(closest);
    expect(closestCopy).toMatch(/Public post/);
    expect(closestCopy).toMatch(/Post quality criterion sales-lead/);
    expect(closestCopy).toMatch(/closest to/);
    expect(closestCopy).not.toMatch(/farthest/);
    expect(leftoverPairTitle(closest)).toBe("Closest leftover: Public post · sales-lead");
    expect(leftoverPairAriaLabel(closest)).toMatch(/public post/i);
    expect(leftoverPairAriaLabel(closest)).toMatch(/sales-lead/);
  });

  it("lands leftover clicks on the named Post quality criterion, not a generic post open", () => {
    expect(leftoverPairOpenOptions(closest)).toEqual({
      focusCriterionCode: "sales_lead_specificity",
    });
    expect(postQualityCriterionElementId(closest.criterion_code)).toBe(
      "post-quality-criterion-sales_lead_specificity",
    );
    const farthestCopy = leftoverPairNextAction(farthest);
    expect(farthestCopy).toMatch(/Specification revision requested/);
    expect(farthestCopy).toMatch(/Post quality criterion negative/);
    expect(farthestCopy).toMatch(/farthest from/);
    expect(leftoverPairOpenOptions(farthest).focusCriterionCode).toBe(
      "general_sentiment_negative",
    );
    expect(leftoverPairTitle(farthest)).toBe(
      "Farthest leftover: Specification revision requested · negative",
    );
    expect(leftoverCriterionLabel("synthetic_criterion")).toBe("synthetic_criterion");
  });
});
