import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchOperationsDashboard, fetchVoiceTaxonomySummary, type OperationsDashboardResponse } from "../api";
import { setLocale } from "../i18n";
import { OperationsDashboard, OperationsDashboardView } from "./OperationsDashboard";

vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  fetchOperationsDashboard: vi.fn(),
  fetchVoiceTaxonomySummary: vi.fn(),
}));

beforeEach(() => {
  setLocale("ko");
  vi.mocked(fetchVoiceTaxonomySummary).mockReset().mockResolvedValue({
    total_eligible: 0, classified_unique: 0, multi_membership: 0,
    source_count: 0, derived_count: 0, unavailable: 0, disagreement: 0,
    counts_overlap: true, category_memberships: [],
  });
});

const data: OperationsDashboardResponse = {
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
  lifecycle_metrics: [
    { lifecycle_kind_code: "claim_investigation", lifecycle_kind_label: "클레임 원인 규명", open_case_count: 1, resolved_case_count: 0, evidence_missing_case_count: 0 },
  ],
  topic_context: {
    status_code: "unavailable",
    reason_code: "tepp_topic_posterior_not_persisted",
    next_action: "TEPP posterior topic 계약 결과를 먼저 완료하세요.",
    required_contracts: [
      { authority: "TEPP", schema_version: "tepp.topic_context_posterior.v1", state_code: "not_persisted" },
      { authority: "fast-mlsirm", schema_version: "fast_mlsirm.topic_context_influence.v1", state_code: "not_persisted" },
    ],
    model_run: null,
    topics: [],
  },
  cases: [{
    post_id: "post-1", case_kind_code: "claim_investigation", case_kind_label: "클레임 원인 역추적",
    project_name: "Synthetic Grid Upgrade", summary_text: "사양 변경 이후 원인 수주를 확인했습니다.", evidence_text: "Revision B changed the enclosure.", evidence_post_id: "evidence-post-1", occurred_at: "2026-08-12T00:00:00Z",
    facts: [{ fact_type_code: "originating_order", fact_type_label: "원인 수주", value_text: "ORDER-100", evidence_text: "Original order ORDER-100", evidence_post_id: "evidence-post-2" }],
    missing_facts: [{ fact_type_code: "sales_pool", fact_type_label: "수주 Pool" }],
    milestones: [
      { milestone_type_code: "claim_received", milestone_type_label: "클레임 접수", evidence_text: "Claim received", evidence_post_id: "evidence-post-1", observed_at: "2026-08-01T09:00:00Z", time_axis_code: "event_occurred_at", time_axis_label: "Event 발생일" },
      { milestone_type_code: "cause_confirmed", milestone_type_label: "원인 확정", evidence_text: "Cause confirmed", evidence_post_id: "evidence-post-2", observed_at: "2026-08-03T12:30:00Z", time_axis_code: "created_at", time_axis_label: "기록 생성일" },
    ],
    lifecycles: [{ lifecycle_kind_code: "claim_investigation", lifecycle_kind_label: "클레임 원인 규명", status_code: "resolved", status_label: "종료 확인", started_at: "2026-08-01T09:00:00Z", resolved_at: "2026-08-03T12:30:00Z", elapsed_seconds: 185400, start_milestone: { milestone_type_code: "claim_received", milestone_type_label: "클레임 접수", evidence_text: "Claim received", evidence_post_id: "evidence-post-1", observed_at: "2026-08-01T09:00:00Z", time_axis_code: "event_occurred_at", time_axis_label: "Event 발생일" }, end_milestone: { milestone_type_code: "cause_confirmed", milestone_type_label: "원인 확정", evidence_text: "Cause confirmed", evidence_post_id: "evidence-post-2", observed_at: "2026-08-03T12:30:00Z", time_axis_code: "created_at", time_axis_label: "기록 생성일" }, next_action_text: "시작·종료 Event 근거를 열어 경과 시간을 검토하세요." }],
  }],
};

describe("OperationsDashboardView", () => {
  it("uses the selected locale for dashboard and topic-influence copy", () => {
    setLocale("en");
    render(<OperationsDashboardView data={data} onOpenPost={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Operations evidence dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Topic model influence over time" })).toBeInTheDocument();
    expect(screen.getByText("Post influence is not available yet.")).toBeInTheDocument();
    expect(screen.queryByText("운영 근거 Dashboard")).not.toBeInTheDocument();
  });

  it("distinguishes posts, events, percentages and opens evidence", async () => {
    const onOpenPost = vi.fn();
    render(<OperationsDashboardView data={data} onOpenPost={onOpenPost} />);
    expect(screen.getByText("3 Event · 2글")).toBeInTheDocument();
    expect(screen.getByText("5건 · 25.0%")).toBeInTheDocument();
    expect(screen.getByText("원인 수주")).toBeInTheDocument();
    expect(screen.getByText(/수주 Pool: 관련 근거를 찾으면 자동으로 다시 분석합니다. 이후 결과를 다시 확인하세요/)).toBeInTheDocument();
    expect(screen.getByText("2일 3시간 30분 0초")).toBeInTheDocument();
    expect(screen.getByText(/진행 중 1건 · 종료 확인 0건/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "분류 근거 글 열기" }));
    expect(onOpenPost).toHaveBeenCalledWith("evidence-post-1");
    await userEvent.click(screen.getByRole("button", { name: "원인 수주 근거 열기" }));
    expect(onOpenPost).toHaveBeenCalledWith("evidence-post-2");
    await userEvent.click(screen.getByRole("button", { name: "클레임 접수 근거 열기" }));
    expect(onOpenPost).toHaveBeenCalledWith("evidence-post-1");
  });

  it("does not imply that only the end evidence is missing", () => {
    const openLifecycle = {
      ...data.cases[0].lifecycles[0],
      status_code: "evidence_missing" as const,
      status_label: "측정 근거 부족",
      started_at: null,
      resolved_at: null,
      elapsed_seconds: null,
      start_milestone: null,
      end_milestone: null,
    };
    render(<OperationsDashboardView data={{ ...data, cases: [{ ...data.cases[0], lifecycles: [openLifecycle] }] }} onOpenPost={() => undefined} />);
    expect(screen.getByText("경과 시간은 필요한 시작·종료 Event 근거가 모두 관측될 때 계산됩니다.")).toBeInTheDocument();
  });

  it("shows an actionable empty external-information state", () => {
    render(<OperationsDashboardView data={data} externalOnly onOpenPost={() => undefined} />);
    expect(screen.getByRole("status")).toHaveTextContent("기간이나 접근 범위를 확인하세요");
    expect(screen.queryByText("분석 대기")).not.toBeInTheDocument();
    expect(screen.queryByText("분석 실패")).not.toBeInTheDocument();
    expect(screen.queryByText("전체 글")).not.toBeInTheDocument();
    expect(screen.queryByText("분류 Event")).not.toBeInTheDocument();
  });

  it("shows external information as a share of all visible posts in the GNB view", () => {
    render(<OperationsDashboardView data={data} externalOnly onOpenPost={() => undefined} />);
    expect(screen.getByText("외부 정보 (전체 글 대비)")).toBeInTheDocument();
    expect(screen.getByText("5건 · 25.0%")).toBeInTheDocument();
  });

  it("labels a source-backed external relation by its semantic target", () => {
    const externalCase = {
      ...data.cases[0],
      case_kind_code: "external_information",
      facts: [{
        ...data.cases[0].facts[0],
        fact_type_code: "external_relation",
        fact_type_label: "업무 관계",
        relation_target_kind_code: "project" as const,
        relation_target_kind_label: "프로젝트",
      }],
      missing_facts: [],
    };
    render(<OperationsDashboardView data={{ ...data, cases: [externalCase] }} onOpenPost={() => undefined} />);
    expect(screen.getByText("업무 관계 · 프로젝트")).toBeInTheDocument();
  });

  it("places multi-project evidence in every observed-event group without calling it a journey", () => {
    const later = { ...data.cases[0], post_id: "post-later", occurred_at: "2026-08-20T00:00:00Z", project_names: ["Synthetic Grid Upgrade", "Synthetic Relay Renewal"] };
    const earlier = { ...data.cases[0], post_id: "post-earlier", occurred_at: "2026-08-01T00:00:00Z", project_names: ["Synthetic Grid Upgrade"] };
    render(<OperationsDashboardView data={{ ...data, cases: [later, earlier] }} onOpenPost={() => undefined} />);

    expect(screen.getByRole("heading", { name: "프로젝트별 관측 Event" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "프로젝트 여정" })).not.toBeInTheDocument();
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

  it("keeps unavailable topic measurement actionable without a fallback score", () => {
    render(<OperationsDashboardView data={data} onOpenPost={() => undefined} />);
    expect(screen.getByText("글 영향도를 아직 확인할 수 없습니다.")).toBeInTheDocument();
    expect(screen.getByText("분석 대상 글의 사건 시점과 조직 소속을 확인한 뒤 다시 분석하세요.")).toBeInTheDocument();
    expect(screen.queryByText(/TEPP|fast-mlsirm|topic_context_posterior/)).not.toBeInTheDocument();
    expect(screen.queryByText(/추정 점수/)).not.toBeInTheDocument();
  });

  it("opens accepted exact influence evidence and retains equal values", async () => {
    const onOpenPost = vi.fn();
    const influence = {
      post_id: "post-1", occurred_at: "2026-08-12T00:00:00Z", topic_state_code: "active" as const,
      model_influence: 4.25, uncertainty_method_code: "posterior_interval",
      uncertainty_lower_value: 3.5, uncertainty_upper_value: 5,
      diagnostic_status_code: "accepted" as const, membership_weight: 0.5,
      membership_evidence_sha256: "a".repeat(64),
    };
    const accepted: OperationsDashboardResponse = {
      ...data,
      topic_context: {
        status_code: "accepted", reason_code: null, next_action: "근거 글을 확인하세요.",
        required_contracts: [
          { authority: "TEPP", schema_version: "tepp.topic_context_posterior.v1", state_code: "persisted" },
          { authority: "fast-mlsirm", schema_version: "fast_mlsirm.topic_context_influence.v1", state_code: "persisted" },
        ],
        model_run: {
          tepp_run_id: "tepp-run", tepp_snapshot_id: "tepp-snapshot", source_snapshot_sha256: "b".repeat(64),
          knowledge_cutoff: "2026-08-20T00:00:00Z", tepp_model_contract_version: "trsl-tm-1",
          tepp_artifact_sha256: "c".repeat(64), posterior_draw_set_id: "draws-1", posterior_draw_count: 32,
          topic_count: 2, fast_mlsirm_version: "0.1.0", fast_mlsirm_code_revision: "d".repeat(40),
          fast_mlsirm_artifact_sha256: "e".repeat(64), compute_backend_code: "rust_cpu", precision_code: "f64",
          membership_fingerprint_sha256: "f".repeat(64),
        },
        topics: [{ topic_index: 0, activity_intervals: [{ state_code: "active", valid_from: "2026-08-01T00:00:00Z", valid_to: "2026-09-01T00:00:00Z" }], lineage_events: [{ event_code: "birth", source_topic_index: 0, target_topic_index: null, event_time: "2026-08-01T00:00:00Z", evidence_sha256: "1".repeat(64) }], contexts: [{ dimension_code: "team", context_id: "team-1", context_label: "Synthetic Team", influences: [influence, { ...influence, post_id: "post-2" }] }] }],
      },
    };
    render(<OperationsDashboardView data={accepted} onOpenPost={onOpenPost} />);
    expect(screen.getAllByText("4.25")).toHaveLength(2);
    expect(screen.getByText((_, element) => element?.tagName === "LI" && element.textContent === "2026-08-01 · birth")).toBeInTheDocument();
    expect(screen.getByText("분석 기준 확인")).toBeInTheDocument();
    expect(screen.queryByText(/tepp-snapshot|fast-mlsirm|rust_gpu/)).not.toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "근거 글 열기" })[1]);
    expect(onOpenPost).toHaveBeenCalledWith("post-2");
  });

  it("keeps period controls mounted while a changed period loads", async () => {
    vi.mocked(fetchVoiceTaxonomySummary).mockResolvedValue({
      total_eligible: 0, classified_unique: 0, multi_membership: 0,
      source_count: 0, derived_count: 0, unavailable: 0, disagreement: 0,
      counts_overlap: true, category_memberships: [],
    });
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

  it("requests the external scope at the API boundary", async () => {
    vi.mocked(fetchVoiceTaxonomySummary).mockClear();
    vi.mocked(fetchOperationsDashboard).mockReset().mockResolvedValue(data);
    render(<OperationsDashboard accessToken="synthetic-token" externalOnly onOpenPost={() => undefined} />);
    await screen.findByText("5건 · 25.0%");
    expect(fetchOperationsDashboard).toHaveBeenCalledWith("synthetic-token", "", "", true);
    expect(fetchVoiceTaxonomySummary).not.toHaveBeenCalled();
  });

  it("shows a failed voice summary and retries only that evidence", async () => {
    vi.mocked(fetchOperationsDashboard).mockReset().mockResolvedValue(data);
    vi.mocked(fetchVoiceTaxonomySummary)
      .mockReset()
      .mockRejectedValueOnce(new Error("synthetic transport failure"))
      .mockResolvedValueOnce({
        total_eligible: 0, classified_unique: 0, multi_membership: 0,
        source_count: 0, derived_count: 0, unavailable: 0, disagreement: 0,
        counts_overlap: true, category_memberships: [],
      });
    render(<OperationsDashboard accessToken="synthetic-token" onOpenPost={() => undefined} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("글 유형 근거를 불러오지 못했습니다.");
    await userEvent.click(screen.getByRole("button", { name: "글 유형 근거 다시 시도" }));
    expect(await screen.findByRole("heading", { name: "글 유형 근거 현황" })).toBeInTheDocument();
    expect(fetchVoiceTaxonomySummary).toHaveBeenCalledTimes(2);
    expect(fetchOperationsDashboard).toHaveBeenCalledTimes(1);
  });

  it("keeps voice evidence actionable when the dashboard request fails", async () => {
    vi.mocked(fetchOperationsDashboard).mockReset().mockRejectedValue(new Error("synthetic dashboard failure"));
    vi.mocked(fetchVoiceTaxonomySummary).mockReset().mockResolvedValue({
      total_eligible: 0, classified_unique: 0, multi_membership: 0,
      source_count: 0, derived_count: 0, unavailable: 0, disagreement: 0,
      counts_overlap: true, category_memberships: [],
    });
    render(<OperationsDashboard accessToken="synthetic-token" onOpenPost={() => undefined} />);

    expect(await screen.findByText("대시보드 근거를 불러오지 못했습니다.")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "글 유형 근거 현황" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument();
  });
});

describe("OperationsDashboard", () => {
  it("announces concurrent dashboard and voice loading through one status region", () => {
    vi.mocked(fetchOperationsDashboard).mockImplementation(() => new Promise(() => undefined));
    vi.mocked(fetchVoiceTaxonomySummary).mockImplementation(() => new Promise(() => undefined));
    render(<OperationsDashboard accessToken="synthetic-token" onOpenPost={() => undefined} />);
    expect(screen.getAllByRole("status")).toHaveLength(1);
    expect(screen.getByRole("status")).toHaveTextContent("대시보드 근거를 불러오는 중입니다.");
    expect(screen.getByRole("status")).toHaveTextContent("글 유형 근거를 불러오는 중입니다...");
  });
});
