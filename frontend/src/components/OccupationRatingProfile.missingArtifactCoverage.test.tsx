import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import type { OccupationRatingProfile as Payload } from "../api";
import { OccupationRatingProfileView } from "./OccupationRatingProfile";

const profileWithoutArtifactLinks: Payload = {
  data_release_code: "onet-31.0",
  source_table_code: "abilities",
  onetsoc_code: "15-1252.00",
  source_available: true,
  source: {
    source_table_name: "Abilities",
    source_artifact_url: "",
    source_artifact_sha256: "a".repeat(64),
    source_row_count: 2,
    scale_artifact_url: "",
    scale_artifact_sha256: "b".repeat(64),
    scale_source_row_count: 33,
  },
  items: [{
    element_id: "1.A.1.a.1",
    element_name: "Oral Comprehension",
    scale_id: "IM",
    scale_name: "Importance",
    minimum_value: "1.00",
    maximum_value: "5.00",
    category_value: null,
    data_value: "4.10",
    sample_size: 120,
    standard_error: "0.0800",
    lower_ci_bound: "3.9432",
    upper_ci_bound: "4.2568",
    recommend_suppress: false,
    not_relevant: false,
    source_updated_month: "08/2026",
    domain_source_code: "Analyst",
  }],
  next_offset: null,
};

it("keeps occupation evidence visible when source artifact links are absent", () => {
  render(<OccupationRatingProfileView profile={profileWithoutArtifactLinks} />);

  expect(screen.getByText("4.10")).toBeInTheDocument();
  expect(screen.getByText(/원문 링크를 사용할 수 없습니다/)).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "평정 원문 열기" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "척도 정의 열기" })).not.toBeInTheDocument();
});
