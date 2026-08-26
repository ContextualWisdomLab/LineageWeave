import { fireEvent, render, screen } from "@testing-library/react";
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

beforeEach(() => {
  vi.mocked(fetchOccupationRatings).mockClear();
  vi.mocked(fetchOccupationRatingSources).mockResolvedValue({
    sources: [{
      data_release_code: "onet-31.0", release_version: "31.0",
      source_publisher_name: "Synthetic publisher", source_license_url: "https://example.test/license",
      source_table_code: "abilities", source_table_name: "Abilities",
      source_artifact_url: "https://example.test/abilities.csv", source_artifact_sha256: "a".repeat(64),
      source_row_count: 2,
    }],
  });
  vi.mocked(fetchRatingSourceOccupations).mockResolvedValue({
    data_release_code: "onet-31.0",
    source_table_code: "abilities",
    source_available: true,
    occupations: [
      { onetsoc_code: "11-1011.00", occupation_title: "Chief Executives" },
      { onetsoc_code: "15-1252.00", occupation_title: "Software Developers" },
    ],
  });
});

describe("OccupationRatingProfile", () => {
  it("submits exact identifiers and renders warnings beside the retained value", async () => {
    vi.mocked(fetchOccupationRatingSources).mockResolvedValue({
      sources: [{
        data_release_code: "onet-31.0", release_version: "31.0",
        source_publisher_name: "Synthetic publisher", source_license_url: "https://example.test/license",
        source_table_code: "abilities", source_table_name: "Abilities",
        source_artifact_url: "https://example.test/abilities.csv", source_artifact_sha256: "a".repeat(64),
        source_row_count: 2,
      }],
    });
    vi.mocked(fetchOccupationRatings).mockResolvedValue(ready);
    render(<OccupationRatingProfile accessToken="synthetic-token" />);
    expect(await screen.findByRole("option", { name: "31.0 · Abilities" })).toBeInTheDocument();
    await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });
    await userEvent.selectOptions(
      await screen.findByLabelText("직업"),
      "15-1252.00",
    );
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));
    expect(fetchOccupationRatings).toHaveBeenCalledWith("synthetic-token", {
      onetsocCode: "15-1252.00", dataReleaseCode: "onet-31.0", sourceTableCode: "abilities", offset: 0,
    });
    expect(await screen.findByText("4.10")).toBeInTheDocument();
    expect(screen.getByText(/정밀도가 낮아/)).toBeInTheDocument();
    expect(screen.getByText(/해당 없음 응답이 포함됩니다/)).toBeInTheDocument();
    expect(screen.getByText(/표를 가로로 밀어/)).toBeInTheDocument();
  });

  it("fails closed when no imported rating source exists", async () => {
    vi.mocked(fetchOccupationRatingSources).mockResolvedValue({ sources: [] });
    render(<OccupationRatingProfile accessToken="synthetic-token" />);

    expect(await screen.findByText(/가져온 직업 근거 표가 없습니다/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "직업 근거 열기" })).toBeDisabled();
  });

  it("fails closed when an imported source has no selectable occupation", async () => {
    vi.mocked(fetchOccupationRatingSources).mockResolvedValue({
      sources: [{
        data_release_code: "onet-31.0", release_version: "31.0",
        source_publisher_name: "Synthetic publisher", source_license_url: "https://example.test/license",
        source_table_code: "abilities", source_table_name: "Abilities",
        source_artifact_url: "https://example.test/abilities.csv", source_artifact_sha256: "a".repeat(64),
        source_row_count: 2,
      }],
    });
    vi.mocked(fetchRatingSourceOccupations).mockResolvedValue({
      data_release_code: "onet-31.0", source_table_code: "abilities",
      source_available: true, occupations: [],
    });
    render(<OccupationRatingProfile accessToken="synthetic-token" />);

    expect(await screen.findByText(/선택할 수 있는 직업이 없습니다/)).toBeInTheDocument();
    expect(screen.getByLabelText("직업")).toBeDisabled();
  });

  it("distinguishes an unavailable occupation catalog from an empty one", async () => {
    vi.mocked(fetchRatingSourceOccupations).mockResolvedValue({
      data_release_code: "onet-31.0", source_table_code: "abilities",
      source_available: false, occupations: [],
    });
    render(<OccupationRatingProfile accessToken="synthetic-token" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("직업 목록을 확인하지 못했습니다");
    expect(screen.queryByText(/선택할 수 있는 직업이 없습니다/)).not.toBeInTheDocument();
  });

  it("clears a stale catalog error when authentication changes", async () => {
    vi.mocked(fetchOccupationRatingSources)
      .mockRejectedValueOnce(new Error("synthetic catalog failure"))
      .mockResolvedValueOnce({ sources: [{
        data_release_code: "onet-31.0", release_version: "31.0",
        source_publisher_name: "Synthetic publisher", source_license_url: "https://example.test/license",
        source_table_code: "abilities", source_table_name: "Abilities",
        source_artifact_url: "https://example.test/abilities.csv", source_artifact_sha256: "a".repeat(64),
        source_row_count: 2,
      }] });
    const { rerender } = render(<OccupationRatingProfile accessToken="expired-token" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("근거 표를 확인하지 못했습니다");

    rerender(<OccupationRatingProfile accessToken="fresh-token" />);

    expect(await screen.findByRole("option", { name: "31.0 · Abilities" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("filters stored titles and submits only the selected catalog identity", async () => {
    vi.mocked(fetchOccupationRatings).mockResolvedValue(ready);
    render(<OccupationRatingProfile accessToken="synthetic-token" />);
    await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });

    await userEvent.type(screen.getByLabelText("직업 찾기"), "15-1252");
    expect(screen.queryByRole("option", { name: "Chief Executives · 11-1011.00" })).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("직업"), "15-1252.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));

    expect(fetchOccupationRatings).toHaveBeenCalledWith("synthetic-token", {
      onetsocCode: "15-1252.00", dataReleaseCode: "onet-31.0", sourceTableCode: "abilities", offset: 0,
    });
  });

  it("fails closed when the title filter matches no catalog occupation", async () => {
    render(<OccupationRatingProfile accessToken="synthetic-token" />);
    await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });

    await userEvent.type(screen.getByLabelText("직업 찾기"), "unknown-occupation");

    expect(await screen.findByText(/입력한 조건에 맞는 직업이 없습니다/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "직업 근거 열기" })).toBeDisabled();
    expect(fetchOccupationRatings).not.toHaveBeenCalled();
  });

  it("clears loaded evidence when the occupation selection changes", async () => {
    vi.mocked(fetchOccupationRatingSources).mockResolvedValue({
      sources: [{
        data_release_code: "onet-31.0", release_version: "31.0",
        source_publisher_name: "Synthetic publisher", source_license_url: "https://example.test/license",
        source_table_code: "abilities", source_table_name: "Abilities",
        source_artifact_url: "https://example.test/abilities.csv", source_artifact_sha256: "a".repeat(64),
        source_row_count: 2,
      }],
    });
    vi.mocked(fetchOccupationRatings).mockResolvedValueOnce({ ...ready, next_offset: 100 });
    render(<OccupationRatingProfile accessToken="synthetic-token" />);
    const occupation = await screen.findByLabelText("직업");
    await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });
    await userEvent.selectOptions(occupation, "15-1252.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));
    await screen.findByText("4.10");

    await userEvent.selectOptions(occupation, "11-1011.00");

    expect(screen.queryByText("4.10")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "다음 관측값 불러오기" })).not.toBeInTheDocument();
  });

  it("removes stale evidence while a fresh occupation loads", async () => {
    vi.mocked(fetchOccupationRatingSources).mockResolvedValue({
      sources: [{
        data_release_code: "onet-31.0", release_version: "31.0",
        source_publisher_name: "Synthetic publisher", source_license_url: "https://example.test/license",
        source_table_code: "abilities", source_table_name: "Abilities",
        source_artifact_url: "https://example.test/abilities.csv", source_artifact_sha256: "a".repeat(64),
        source_row_count: 2,
      }],
    });
    vi.mocked(fetchOccupationRatings)
      .mockResolvedValueOnce(ready)
      .mockImplementationOnce(() => new Promise(() => undefined));
    render(<OccupationRatingProfile accessToken="synthetic-token" />);
    const occupation = await screen.findByLabelText("직업");
    await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });
    await userEvent.selectOptions(occupation, "15-1252.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));
    await screen.findByText("4.10");

    await userEvent.selectOptions(occupation, "11-1011.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));

    expect(screen.queryByText("4.10")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "근거를 불러오는 중" })).toBeDisabled();
  });

  it("ignores a superseded occupation response that finishes last", async () => {
    let finishFirst: ((profile: Payload) => void) | undefined;
    vi.mocked(fetchOccupationRatingSources).mockResolvedValue({ sources: [{
      data_release_code: "onet-31.0", release_version: "31.0",
      source_publisher_name: "Synthetic publisher", source_license_url: "https://example.test/license",
      source_table_code: "abilities", source_table_name: "Abilities",
      source_artifact_url: "https://example.test/abilities.csv", source_artifact_sha256: "a".repeat(64),
      source_row_count: 2,
    }] });
    vi.mocked(fetchOccupationRatings)
      .mockImplementationOnce(() => new Promise((resolve) => { finishFirst = resolve; }))
      .mockResolvedValueOnce({ ...ready, onetsoc_code: "11-1011.00", items: [{ ...ready.items[0], data_value: "3.20" }] });
    render(<OccupationRatingProfile accessToken="synthetic-token" />);
    const occupation = await screen.findByLabelText("직업");
    await screen.findByRole("option", { name: "Software Developers · 15-1252.00" });
    await userEvent.selectOptions(occupation, "15-1252.00");
    await userEvent.click(screen.getByRole("button", { name: "직업 근거 열기" }));

    await userEvent.selectOptions(occupation, "11-1011.00");
    fireEvent.submit(occupation.closest("form")!);
    expect(await screen.findByText("3.20")).toBeInTheDocument();

    finishFirst?.(ready);
    expect(screen.queryByText("4.10")).not.toBeInTheDocument();
    expect(screen.getByText("3.20")).toBeInTheDocument();
  });

  it("distinguishes an unavailable artifact from an empty occupation profile", () => {
    const { rerender } = render(<OccupationRatingProfileView profile={{ ...ready, source_available: false, source: null, items: [] }} />);
    expect(screen.getByRole("status")).toHaveTextContent("아직 준비되지 않았습니다");
    rerender(<OccupationRatingProfileView profile={{ ...ready, items: [] }} />);
    expect(screen.getByRole("status")).toHaveTextContent("관측값이 없습니다");
  });

  it("does not turn a non-http artifact value into a customer link", () => {
    render(<OccupationRatingProfileView profile={{
      ...ready,
      source: { ...ready.source!, source_artifact_url: "javascript:alert(1)" },
    }} />);

    expect(screen.queryByRole("link", { name: "평정 원문 열기" })).not.toBeInTheDocument();
    expect(screen.getByText(/데이터 담당자에게 출처 확인을 요청하세요/)).toBeInTheDocument();
  });
});
