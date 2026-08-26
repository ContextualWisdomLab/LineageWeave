import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VoiceTaxonomySummary } from "./VoiceTaxonomySummary";

describe("VoiceTaxonomySummary", () => {
  it("discloses overlapping counts and the next review action", () => {
    render(<VoiceTaxonomySummary data={{
      total_eligible: 2, classified_unique: 0, multi_membership: 1,
      source_count: 1, derived_count: 1, unavailable: 1, disagreement: 1,
      counts_overlap: true, next_action_text: "Review evidence.",
      category_memberships: [{ voice_concept_code: "voc", post_count: 1, eligible_percentage: 50 }],
    }} />);
    expect(screen.getByText(/중복될 수 있습니다/)).toBeInTheDocument();
    expect(screen.getByText(/확인한 뒤 분류를 활용하세요/)).toBeInTheDocument();
  });
});
