import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchOccupationRatingSources,
  fetchOccupationRatings,
  fetchRatingSourceOccupations,
  type OccupationRatingProfile as Payload,
} from "../api";
import { OccupationRatingProfile, OccupationRatingProfileView } from "./OccupationRatingProfile";

vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  fetchOccupationRatingSources: vi.fn(),
  fetchOccupationRatings: vi.fn(),
  fetchRatingSourceOccupations: vi.fn(),
}));

const abilitiesSource = {
  data_release_code: "onet-31.0",
  release_version: "31.0",
  source_publisher_name: "Synthetic publisher",
  source_license_url: "https://example.test/license",
  source_table_code: "abilities",
  source_table_name: "Abilities",
  source_artifact_url: "https://example.test/abilities.csv",
  source_artifact_sha256: "a".repeat(64),
  source_row_count: 2,
};

const interestsSource = {
  ...abilitiesSource,
  source_table_code: "interests",
  source_table_name: "Interests",
  source_artifact_url: "https://example.test/interests.csv",
};

const ready: Payload = {
  data_release_code: "onet-31.0",
  source_table_code: "abilities",
  onetsoc_code: "15-1252.00",
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
    data_value: "4.10",
    sample_size: 120,
    standard_error: "0.0800",
    lower_ci_bound: "3.9432",
    upper_ci_bound: "4.2568",
    recommend_suppress: true,
    not_relevant: true,
    source_updated_month: "08/2026",
    domain_source_code: "Analyst",
  }],
  next_offset: null,
};

beforeEach(() => {
  vi.mocked(fetchOccupationRatingSources).mockReset();
  vi.mocked(fetchOccupationRatings).mockReset();
  vi.mocked(fetchRatingSourceOccupations).mockReset();
  vi.mocked(fetchOccupationRatingSources).mockResolvedValue({
    sources: [abilitiesSource, interestsSource],
  });
  vi.mocked(fetchRatingSourceOccupations).mockImplementation(
    async (_accessToken, _releaseCode, sourceTableCode) => ({
      data_release_code: "onet-31.0",
      source_table_code: sourceTableCode,
      source_available: true,
      occupations: sourceTableCode === "interests"
        ? [{ onetsoc_code: "11-1011.00", occupation_title: "Chief Executives" }]
        : [
            { onetsoc_code: "11-1011.00", occupation_title: "Chief Executives" },
            { onetsoc_code: "15-1252.00", occupation_title: "Software Developers" },
          ],
    }),
  );
});

describe("OccupationRatingProfile coverage contracts", () => {
  it("retires loaded evidence when the search filter excludes the selected occupation", async () => {
    vi.mocked(fetchOccupationRatings).mockResolvedValue(ready);
    render(<OccupationRatingProfile accessToken="synthetic-token" />);

    const occupation = await screen.findByLabelText("직업");
    await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });
    await userEvent.selectOptions(occupation, "15-1252.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));
    expect(await screen.findByText("4.10")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("직업 찾기"), "Chief");

    expect(occupation).toHaveValue("");
    expect(screen.queryByText("4.10")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "직업 근거 열기" })).toBeDisabled();
  });

  it("reloads the occupation catalog and clears the selection when the evidence source changes", async () => {
    render(<OccupationRatingProfile accessToken="synthetic-token" />);

    const occupation = await screen.findByLabelText("직업");
    await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });
    await userEvent.selectOptions(occupation, "15-1252.00");

    await userEvent.selectOptions(screen.getByLabelText("근거 릴리스·표"), "onet-31.0|interests");

    await waitFor(() => expect(fetchRatingSourceOccupations).toHaveBeenLastCalledWith(
      "synthetic-token",
      "onet-31.0",
      "interests",
    ));
    expect(occupation).toHaveValue("");
    expect(await screen.findByRole("option", { name: "Chief Executives · 11-1011.00" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Software Developers · 15-1252.00" })).not.toBeInTheDocument();
  });

  it("appends the next page using the admitted profile identity", async () => {
    vi.mocked(fetchOccupationRatings)
      .mockResolvedValueOnce({ ...ready, next_offset: 100 })
      .mockResolvedValueOnce({
        ...ready,
        items: [{ ...ready.items[0], element_id: "1.A.1.a.2", data_value: "3.20" }],
        next_offset: null,
      });
    render(<OccupationRatingProfile accessToken="synthetic-token" />);

    await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });
    await userEvent.selectOptions(screen.getByLabelText("직업"), "15-1252.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));
    expect(await screen.findByText("4.10")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "다음 관측값 불러오기" }));

    expect(await screen.findByText("3.20")).toBeInTheDocument();
    expect(screen.getByText("4.10")).toBeInTheDocument();
    expect(fetchOccupationRatings).toHaveBeenNthCalledWith(2, "synthetic-token", {
      onetsocCode: "15-1252.00",
      dataReleaseCode: "onet-31.0",
      sourceTableCode: "abilities",
      offset: 100,
    });
  });

  it("surfaces a bounded error when the current rating request fails", async () => {
    vi.mocked(fetchOccupationRatings).mockRejectedValue(new Error("synthetic rating failure"));
    render(<OccupationRatingProfile accessToken="synthetic-token" />);

    await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });
    await userEvent.selectOptions(screen.getByLabelText("직업"), "15-1252.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("직업 근거를 불러오지 못했습니다");
  });

  it("keeps syntactically invalid artifact locations out of customer links", () => {
    render(<OccupationRatingProfileView profile={{
      ...ready,
      source: {
        ...ready.source!,
        source_artifact_url: "not a URL",
        scale_artifact_url: "also not a URL",
      },
    }} />);

    expect(screen.queryByRole("link", { name: "평정 원문 열기" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "척도 정의 열기" })).not.toBeInTheDocument();
    expect(screen.getByText(/데이터 담당자에게 출처 확인을 요청하세요/)).toBeInTheDocument();
  });
});
