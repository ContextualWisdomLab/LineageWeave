import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { setLocale } from "../i18n";
import { VoiceTaxonomySummary } from "./VoiceTaxonomySummary";

describe("VoiceTaxonomySummary", () => {
  afterEach(() => setLocale("en"));

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

  it("updates every visible label when the product locale changes", () => {
    render(<VoiceTaxonomySummary data={{
      total_eligible: 2, classified_unique: 2, multi_membership: 0,
      source_count: 2, derived_count: 0, unavailable: 0, disagreement: 0,
      counts_overlap: false,
      category_memberships: [{ voice_concept_code: "voc", post_count: 2, eligible_percentage: 100 }],
    }} />);

    act(() => setLocale("ko"));

    expect(screen.getByRole("heading", { name: "글 유형 근거 현황" })).toBeInTheDocument();
    expect(screen.getByText("기록된 근거")).toBeInTheDocument();
    expect(screen.getByText("글 유형 근거가 없는 기록")).toBeInTheDocument();
    expect(screen.getByText("고객의 소리")).toBeInTheDocument();
    expect(screen.getByText(/불일치와 글 유형 근거가 없는 기록을 확인한 뒤/)).toBeInTheDocument();
    expect(screen.queryByText("Voice evidence overview")).not.toBeInTheDocument();
  });
});
