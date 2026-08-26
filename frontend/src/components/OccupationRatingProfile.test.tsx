import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { fetchOccupationRatings, type OccupationRatingProfile as Payload } from "../api";
import { OccupationRatingProfile, OccupationRatingProfileView } from "./OccupationRatingProfile";

vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  fetchOccupationRatings: vi.fn(),
}));

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
    element_id: "1.A.1.a.1", element_name: "Oral Comprehension",
    scale_id: "IM", scale_name: "Importance", minimum_value: "1.00", maximum_value: "5.00",
    category_value: null, data_value: "4.10", sample_size: 120, standard_error: "0.0800",
    lower_ci_bound: "3.9432", upper_ci_bound: "4.2568", recommend_suppress: true,
    not_relevant: true, source_updated_month: "08/2026", domain_source_code: "Analyst",
  }],
  next_offset: null,
};

describe("OccupationRatingProfile", () => {
  it("submits exact identifiers and renders warnings beside the retained value", async () => {
    vi.mocked(fetchOccupationRatings).mockResolvedValue(ready);
    render(<OccupationRatingProfile accessToken="synthetic-token" />);
    await userEvent.type(screen.getByLabelText("O*NET-SOC 직업 코드"), "15-1252.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));
    expect(fetchOccupationRatings).toHaveBeenCalledWith("synthetic-token", {
      onetsocCode: "15-1252.00", dataReleaseCode: "onet-31.0", sourceTableCode: "abilities", offset: 0,
    });
    expect(await screen.findByText("4.10")).toBeInTheDocument();
    expect(screen.getByText(/정밀도가 낮아/)).toBeInTheDocument();
    expect(screen.getByText(/해당 없음 응답이 포함됩니다/)).toBeInTheDocument();
    expect(screen.getByText(/표를 가로로 밀어/)).toBeInTheDocument();
  });

  it("keeps pagination bound to the loaded profile after form edits", async () => {
    vi.mocked(fetchOccupationRatings)
      .mockResolvedValueOnce({ ...ready, next_offset: 100 })
      .mockResolvedValueOnce({ ...ready, items: [{ ...ready.items[0], scale_id: "LV" }] });
    render(<OccupationRatingProfile accessToken="synthetic-token" />);
    const occupation = screen.getByLabelText("O*NET-SOC 직업 코드");
    await userEvent.type(occupation, "15-1252.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));
    await screen.findByText("4.10");

    await userEvent.clear(occupation);
    await userEvent.type(occupation, "11-1011.00");
    await userEvent.click(screen.getByRole("button", { name: "다음 관측값 불러오기" }));

    expect(fetchOccupationRatings).toHaveBeenLastCalledWith("synthetic-token", {
      onetsocCode: "15-1252.00", dataReleaseCode: "onet-31.0", sourceTableCode: "abilities", offset: 100,
    });
    expect(await screen.findAllByText("4.10")).toHaveLength(2);
  });

  it("removes stale evidence while a fresh occupation loads", async () => {
    vi.mocked(fetchOccupationRatings)
      .mockResolvedValueOnce(ready)
      .mockImplementationOnce(() => new Promise(() => undefined));
    render(<OccupationRatingProfile accessToken="synthetic-token" />);
    const occupation = screen.getByLabelText("O*NET-SOC 직업 코드");
    await userEvent.type(occupation, "15-1252.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));
    await screen.findByText("4.10");

    await userEvent.clear(occupation);
    await userEvent.type(occupation, "11-1011.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));

    expect(screen.queryByText("4.10")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "근거를 불러오는 중" })).toBeDisabled();
  });

  it("distinguishes an unavailable artifact from an empty occupation profile", () => {
    const { rerender } = render(<OccupationRatingProfileView profile={{ ...ready, source_available: false, source: null, items: [] }} />);
    expect(screen.getByRole("status")).toHaveTextContent("아직 준비되지 않았습니다");
    rerender(<OccupationRatingProfileView profile={{ ...ready, items: [] }} />);
    expect(screen.getByRole("status")).toHaveTextContent("관측값이 없습니다");
  });
});
