import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import {
  fetchOccupationRatingSources,
  fetchOccupationRatings,
  fetchRatingSourceOccupations,
  type OccupationRatingProfile as Payload,
} from "../api";
import { OccupationRatingProfile } from "./OccupationRatingProfile";

vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  fetchOccupationRatingSources: vi.fn(),
  fetchOccupationRatings: vi.fn(),
  fetchRatingSourceOccupations: vi.fn(),
}));

const profile: Payload = {
  data_release_code: "onet-31.0",
  source_table_code: "abilities",
  onetsoc_code: "11-1011.00",
  source_available: true,
  source: {
    source_table_name: "Abilities",
    source_artifact_url: "https://example.test/abilities.csv",
    source_artifact_sha256: "a".repeat(64),
    source_row_count: 2,
    scale_artifact_url: "https://example.test/scales.csv",
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
    data_value: "3.20",
    sample_size: 120,
    standard_error: "0.0800",
    lower_ci_bound: "3.0432",
    upper_ci_bound: "3.3568",
    recommend_suppress: false,
    not_relevant: false,
    source_updated_month: "08/2026",
    domain_source_code: "Analyst",
  }],
  next_offset: null,
};

beforeEach(() => {
  vi.mocked(fetchOccupationRatingSources).mockResolvedValue({
    sources: [{
      data_release_code: "onet-31.0",
      release_version: "31.0",
      source_publisher_name: "Synthetic publisher",
      source_license_url: "https://example.test/license",
      source_table_code: "abilities",
      source_table_name: "Abilities",
      source_artifact_url: "https://example.test/abilities.csv",
      source_artifact_sha256: "a".repeat(64),
      source_row_count: 2,
    }],
  });
  vi.mocked(fetchRatingSourceOccupations).mockResolvedValue({
    data_release_code: "onet-31.0",
    source_table_code: "abilities",
    source_available: true,
    occupations: [
      { onetsoc_code: "15-1252.00", occupation_title: "Software Developers" },
      { onetsoc_code: "11-1011.00", occupation_title: "Chief Executives" },
    ],
  });
  vi.mocked(fetchOccupationRatings).mockReset();
});

it("ignores a rejected occupation request after the user has moved to newer evidence", async () => {
  let rejectSuperseded: ((reason?: unknown) => void) | undefined;
  vi.mocked(fetchOccupationRatings)
    .mockImplementationOnce(() => new Promise((_, reject) => { rejectSuperseded = reject; }))
    .mockResolvedValueOnce(profile);

  render(<OccupationRatingProfile accessToken="synthetic-token" />);
  const occupation = await screen.findByLabelText("직업");
  await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });

  await userEvent.selectOptions(occupation, "15-1252.00");
  await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));

  await userEvent.selectOptions(occupation, "11-1011.00");
  await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));
  expect(await screen.findByText("3.20")).toBeInTheDocument();

  await act(async () => {
    rejectSuperseded?.(new Error("superseded transport failure"));
  });

  expect(screen.getByText("3.20")).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
