import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VoiceTaxonomySummary } from "./VoiceTaxonomySummary";

describe("VoiceTaxonomySummary", () => {
  it("discloses overlapping counts and the next review action", () => {
    render(<VoiceTaxonomySummary data={{
      total_eligible: 2, classified_unique: 0, multi_membership: 1,
      source_count: 1, derived_count: 1, unavailable: 1, disagreement: 1,
      counts_overlap: true,
      category_memberships: [{ voice_concept_code: "voc", post_count: 1, eligible_percentage: 50 }],
    }} />);
    expect(screen.getByText(/category counts can overlap/)).toBeInTheDocument();
    expect(screen.getByText(/Review disagreements and records without evidence/)).toBeInTheDocument();
  });
});
