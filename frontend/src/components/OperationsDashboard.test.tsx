import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchOperationsDashboard } from "../api";
import { OperationsDashboard, OperationsDashboardView } from "./OperationsDashboard";

vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  fetchOperationsDashboard: vi.fn(),
}));

const data = {
  period_label: "2026-08-01–2026-08-25 · Event time",
  total_post_count: 20,
  total_event_count: 8,
  external_post_count: 5,
  external_percent: 25,
  pending_analysis_count: 2,
  failed_analysis_count: 0,
  cases: [{
    post_id: "post-1", case_kind_code: "claim_investigation", case_kind_label: "클레임 원인 역추적",
    project_name: "Synthetic Grid Upgrade", summary_text: "사양 변경 이후 원인 수주를 확인했습니다.", evidence_text: "Revision B changed the enclosure.", evidence_post_id: "evidence-post-1", occurred_at: "2026-08-12T00:00:00Z",
    facts: [{ fact_type_code: "originating_order", fact_type_label: "원인 수주", value_text: "ORDER-100", evidence_text: "Original order ORDER-100", evidence_post_id: "evidence-post-2" }],
  }],
};

describe("OperationsDashboardView", () => {
  beforeEach(() => vi.mocked(fetchOperationsDashboard).mockReset());

  it.each(["success", "failure"])("ignores stale %s after the access token changes", async (outcome) => {
    let resolvePrevious!: (value: Awaited<ReturnType<typeof fetchOperationsDashboard>>) => void;
    let rejectPrevious!: (reason: Error) => void;
    const previous = new Promise<Awaited<ReturnType<typeof fetchOperationsDashboard>>>((resolve, reject) => {
      resolvePrevious = resolve;
      rejectPrevious = reject;
    });
    vi.mocked(fetchOperationsDashboard)
      .mockReturnValueOnce(previous)
      .mockResolvedValueOnce({ ...data, period_label: "Current authorized period" });
    const { rerender } = render(<OperationsDashboard accessToken="old-token" onOpenPost={() => undefined} />);
    rerender(<OperationsDashboard accessToken="new-token" onOpenPost={() => undefined} />);
    await screen.findByText("Current authorized period");
    await act(async () => {
      if (outcome === "success") resolvePrevious({ ...data, period_label: "Stale authorized period" });
      else rejectPrevious(new Error("previous request failed"));
    });
    expect(screen.getByText("Current authorized period")).toBeInTheDocument();
    expect(screen.queryByText("Stale authorized period")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(fetchOperationsDashboard).toHaveBeenNthCalledWith(2, "new-token", "", "");
  });

  it("retries a failed query with the selected period and hides diagnostic details", async () => {
    const fetchMock = vi.mocked(fetchOperationsDashboard);
    fetchMock.mockResolvedValueOnce(data)
      .mockRejectedValueOnce(new Error("private upstream diagnostic"))
      .mockResolvedValueOnce(data);
    render(<OperationsDashboard accessToken="synthetic-token" onOpenPost={() => undefined} />);
    await screen.findByText("5건 · 25.0%");
    fireEvent.change(screen.getByLabelText("시작일"), { target: { value: "2026-08-01" } });
    fireEvent.change(screen.getByLabelText("종료일"), { target: { value: "2026-08-25" } });
    await userEvent.click(screen.getByRole("button", { name: "기간 적용" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("불러오지 못했습니다");
    expect(screen.queryByText("private upstream diagnostic")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    await screen.findByText("5건 · 25.0%");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock).toHaveBeenNthCalledWith(2, "synthetic-token", "2026-08-01", "2026-08-25");
    expect(fetchMock).toHaveBeenNthCalledWith(3, "synthetic-token", "2026-08-01", "2026-08-25");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("distinguishes posts, events, percentages and opens evidence", async () => {
    const onOpenPost = vi.fn();
    render(<OperationsDashboardView data={data} onOpenPost={onOpenPost} />);
    expect(screen.getByText("5건 · 25.0%")).toBeInTheDocument();
    expect(screen.getByText("원인 수주")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "분류 근거 글 열기" }));
    expect(onOpenPost).toHaveBeenCalledWith("evidence-post-1");
    await userEvent.click(screen.getByRole("button", { name: "원인 수주 근거 열기" }));
    expect(onOpenPost).toHaveBeenCalledWith("evidence-post-2");
  });

  it("shows an actionable empty external-information state", () => {
    render(<OperationsDashboardView data={data} externalOnly onOpenPost={() => undefined} />);
    expect(screen.getByRole("status")).toHaveTextContent("분석 대기 건부터 처리하세요");
  });

  it("separates failed analysis from pending work and gives the next action", () => {
    render(<OperationsDashboardView data={{ ...data, failed_analysis_count: 2, cases: [] }} onOpenPost={() => undefined} />);
    expect(screen.getByText("분석 실패").nextElementSibling).toHaveTextContent("2");
    expect(screen.getByRole("alert")).toHaveTextContent("재처리한 뒤 근거 누락 여부를 다시 확인하세요");
    expect(screen.queryByText("분석 대기 건부터 처리하세요")).not.toBeInTheDocument();
  });

  it("keeps period controls mounted while a changed period loads", async () => {
    vi.mocked(fetchOperationsDashboard)
      .mockResolvedValueOnce(data)
      .mockImplementationOnce(() => new Promise(() => undefined));
    render(<OperationsDashboard accessToken="synthetic-token" onOpenPost={() => undefined} />);
    await screen.findByText("5건 · 25.0%");
    await userEvent.type(screen.getByLabelText("시작일"), "2026-08-01");
    await userEvent.click(screen.getByRole("button", { name: "기간 적용" }));
    expect(screen.getByLabelText("시작일")).toHaveValue("2026-08-01");
    expect(screen.getByRole("status")).toHaveTextContent("불러오는 중");
  });
});
