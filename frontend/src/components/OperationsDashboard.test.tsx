import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
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
  case_metrics: [
    { case_kind_code: "claim_investigation", case_kind_label: "클레임 원인 규명", event_count: 3, post_count: 2 },
    { case_kind_code: "rebid_handover", case_kind_label: "재입찰 · 인수인계", event_count: 2, post_count: 2 },
  ],
  cases: [{
    post_id: "post-1", case_kind_code: "claim_investigation", case_kind_label: "클레임 원인 역추적",
    project_name: "Synthetic Grid Upgrade", summary_text: "사양 변경 이후 원인 수주를 확인했습니다.", evidence_text: "Revision B changed the enclosure.", evidence_post_id: "evidence-post-1", occurred_at: "2026-08-12T00:00:00Z",
    facts: [{ fact_type_code: "originating_order", fact_type_label: "원인 수주", value_text: "ORDER-100", evidence_text: "Original order ORDER-100", evidence_post_id: "evidence-post-2" }],
    missing_facts: [{ fact_type_code: "sales_pool", fact_type_label: "수주 Pool" }],
  }],
};

describe("OperationsDashboardView", () => {
  it("distinguishes posts, events, percentages and opens evidence", async () => {
    const onOpenPost = vi.fn();
    render(<OperationsDashboardView data={data} onOpenPost={onOpenPost} />);
    expect(screen.getByText("3 Event · 2글")).toBeInTheDocument();
    expect(screen.getByText("5건 · 25.0%")).toBeInTheDocument();
    expect(screen.getByText("원인 수주")).toBeInTheDocument();
    expect(screen.getByText(/수주 Pool: 권한 범위 내 근거가 없습니다/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "분류 근거 글 열기" }));
    expect(onOpenPost).toHaveBeenCalledWith("evidence-post-1");
    await userEvent.click(screen.getByRole("button", { name: "원인 수주 근거 열기" }));
    expect(onOpenPost).toHaveBeenCalledWith("evidence-post-2");
  });

  it("shows an actionable empty external-information state", () => {
    render(<OperationsDashboardView data={data} externalOnly onOpenPost={() => undefined} />);
    expect(screen.getByRole("status")).toHaveTextContent("분석 대기 건부터 처리하세요");
  });

  it("places multi-project evidence in every explicit journey and orders events oldest first", () => {
    const later = { ...data.cases[0], post_id: "post-later", occurred_at: "2026-08-20T00:00:00Z", project_names: ["Synthetic Grid Upgrade", "Synthetic Relay Renewal"] };
    const earlier = { ...data.cases[0], post_id: "post-earlier", occurred_at: "2026-08-01T00:00:00Z", project_names: ["Synthetic Grid Upgrade"] };
    render(<OperationsDashboardView data={{ ...data, cases: [later, earlier] }} onOpenPost={() => undefined} />);

    expect(screen.getByRole("heading", { name: "Synthetic Relay Renewal" })).toBeInTheDocument();
    const primaryJourney = screen.getByRole("heading", { name: "Synthetic Grid Upgrade" }).parentElement;
    expect(primaryJourney?.querySelectorAll("time")[0]).toHaveAttribute("datetime", earlier.occurred_at);
    expect(primaryJourney?.querySelectorAll("time")[1]).toHaveAttribute("datetime", later.occurred_at);
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
