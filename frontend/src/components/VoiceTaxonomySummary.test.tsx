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
    expect(screen.getByRole("heading", { name: "Voice evidence overview" })).toBeInTheDocument();
    expect(screen.getByText("Records in multiple voice categories")).toBeInTheDocument();
    expect(screen.getByText("Records without voice evidence")).toBeInTheDocument();
    expect(screen.getByText(/voice categories, so category counts can overlap/)).toBeInTheDocument();
    expect(screen.getByText(/Review disagreements and records without voice evidence/)).toBeInTheDocument();
  });

  it("renders the canonical process voice label", () => {
    render(<VoiceTaxonomySummary data={{
      total_eligible: 1, classified_unique: 1, multi_membership: 0,
      source_count: 1, derived_count: 0, unavailable: 0, disagreement: 0,
      counts_overlap: false,
      category_memberships: [{ voice_concept_code: "vops", post_count: 1, eligible_percentage: 100 }],
    }} />);

    expect(screen.getByText("Voice of Process")).toBeInTheDocument();
    expect(screen.queryByText("Voice of Prospective customer")).not.toBeInTheDocument();
  });
});
