import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { OperationsDashboard, OperationsDashboardView } from "./OperationsDashboard";
import "../App.css";

const meta = { title: "Workspace/OperationsDashboard", component: OperationsDashboardView, parameters: { layout: "fullscreen" } } satisfies Meta<typeof OperationsDashboardView>;
export default meta;
type Story = StoryObj<typeof meta>;

export const EvidenceReady: Story = {
  args: {
    data: {
      period_label: "2026-08-01–2026-08-25 · Event time", total_post_count: 40, total_event_count: 17,
      external_post_count: 9, external_percent: 22.5, pending_analysis_count: 3,
      case_metrics: [
        { case_kind_code: "claim_investigation", case_kind_label: "클레임 원인 규명", event_count: 7, post_count: 5 },
        { case_kind_code: "rebid_handover", case_kind_label: "재입찰 · 인수인계", event_count: 4, post_count: 3 },
        { case_kind_code: "external_information", case_kind_label: "발주 공고 · 시장 동향", event_count: 9, post_count: 9 },
        { case_kind_code: "repeat_issue", case_kind_label: "반복 이슈", event_count: 2, post_count: 2 },
      ],
      lifecycle_metrics: [
        { lifecycle_kind_code: "claim_investigation", lifecycle_kind_label: "클레임 원인 규명", open_case_count: 1, resolved_case_count: 0, evidence_missing_case_count: 0 },
        { lifecycle_kind_code: "rebid_response", lifecycle_kind_label: "재입찰 대응", open_case_count: 0, resolved_case_count: 1, evidence_missing_case_count: 0 },
        { lifecycle_kind_code: "handover_gap", lifecycle_kind_label: "인수인계 공백", open_case_count: 0, resolved_case_count: 0, evidence_missing_case_count: 1 },
      ],
      topic_context: {
        status_code: "unavailable", reason_code: "tepp_topic_posterior_not_persisted",
        next_action: "TEPP posterior topic 계약 결과를 먼저 완료하세요.", model_run: null, topics: [],
        required_contracts: [
          { authority: "TEPP", schema_version: "tepp.topic_context_posterior.v1", state_code: "not_persisted" },
          { authority: "fast-mlsirm", schema_version: "fast_mlsirm.topic_context_influence.v1", state_code: "not_persisted" },
        ],
      },
      failed_analysis_count: 0,
      cases: [
        { post_id: "synthetic-post-1", case_kind_code: "claim_investigation", case_kind_label: "클레임 원인 역추적", project_name: "Synthetic Transformer Renewal", summary_text: "사양 변경 이후 원인 수주와 Pool을 확인", evidence_text: "Revision B originated in order SO-100 from pool SP-20.", evidence_post_id: "synthetic-post-1", occurred_at: "2026-08-04T00:00:00Z", facts: [{ fact_type_code: "originating_order", fact_type_label: "원인 수주", value_text: "SO-100 · SP-20", evidence_text: "order SO-100 from pool SP-20", evidence_post_id: "synthetic-post-1" }], missing_facts: [{ fact_type_code: "order", fact_type_label: "발생 수주" }, { fact_type_code: "specification_change", fact_type_label: "사양 변경" }, { fact_type_code: "sales_pool", fact_type_label: "수주 Pool" }], milestones: [], lifecycles: [] },
        { post_id: "synthetic-post-2", case_kind_code: "rebid_handover", case_kind_label: "재입찰 · 인수인계", project_name: "Synthetic Transformer Renewal", summary_text: "담당자 교체 전 협의와 후속 결정을 연결", evidence_text: "The account owner and design lead agreed to submit the revised proposal.", evidence_post_id: "synthetic-post-2", occurred_at: "2026-08-11T00:00:00Z", facts: [{ fact_type_code: "decision", fact_type_label: "이어진 결정", value_text: "수정 제안 제출", evidence_text: "submit the revised proposal", evidence_post_id: "synthetic-post-2" }], missing_facts: [{ fact_type_code: "discussion", fact_type_label: "협의 내용" }, { fact_type_code: "counterparty", fact_type_label: "협의 상대" }, { fact_type_code: "our_owner", fact_type_label: "우리측 담당자" }], milestones: [], lifecycles: [] },
        { post_id: "synthetic-post-3", case_kind_code: "external_information", case_kind_label: "외부 정보", project_name: "Synthetic Transformer Renewal", summary_text: "시장 공고를 영업 기회와 연결", evidence_text: "The public procurement notice opened on August 15.", evidence_post_id: "synthetic-post-3", occurred_at: "2026-08-15T00:00:00Z", facts: [{ fact_type_code: "external_relation", fact_type_label: "업무 관계", value_text: "갱신 제안 준비", evidence_text: "procurement notice", evidence_post_id: "synthetic-post-3", relation_target_kind_code: "project", relation_target_kind_label: "프로젝트" }], missing_facts: [], milestones: [], lifecycles: [] },
        { post_id: "synthetic-post-4", case_kind_code: "repeat_issue", case_kind_label: "반복 이슈 반영", project_name: "Synthetic Transformer Renewal", summary_text: "동일 유형 이슈를 설계 개선으로 환류", evidence_text: "The same enclosure issue recurred after Revision B.", evidence_post_id: "synthetic-post-4", occurred_at: "2026-08-18T00:00:00Z", facts: [{ fact_type_code: "improvement_action", fact_type_label: "개선 과제", value_text: "표준 사양 개정", evidence_text: "Update the standard enclosure specification.", evidence_post_id: "synthetic-post-4" }], missing_facts: [{ fact_type_code: "issue_pattern", fact_type_label: "반복 유형" }], milestones: [], lifecycles: [] },
      ],
    },
    onOpenPost: () => undefined,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("9건 · 22.5%")).toBeInTheDocument();
    await expect(canvas.getByText("사건 7건 · 글 5건")).toBeVisible();
    await expect(canvas.getByText("3일 3시간 30분 0초")).toBeVisible();
    await expect(canvas.getAllByRole("button", { name: "분류 근거 글 열기" })[0]).toBeVisible();
  },
};

export const TopicInfluenceAccepted: Story = {
  args: {
    ...EvidenceReady.args,
    data: {
      ...EvidenceReady.args!.data!,
      topic_context: {
        status_code: "accepted", reason_code: null,
        next_action: "Topic과 조직 수준을 선택해 model influence와 근거 글을 확인하세요.",
        required_contracts: [
          { authority: "TEPP", schema_version: "tepp.topic_context_posterior.v1", state_code: "persisted" },
          { authority: "fast-mlsirm", schema_version: "fast_mlsirm.topic_context_influence.v1", state_code: "persisted" },
        ],
        model_run: {
          tepp_run_id: "synthetic-tepp-run", tepp_snapshot_id: "synthetic-tepp-snapshot", source_snapshot_sha256: "a".repeat(64),
          knowledge_cutoff: "2026-08-20T00:00:00Z", tepp_model_contract_version: "trsl-tm-1",
          tepp_artifact_sha256: "b".repeat(64), posterior_draw_set_id: "synthetic-draws",
          posterior_draw_count: 32, topic_count: 2, fast_mlsirm_version: "0.1.0",
          fast_mlsirm_code_revision: "c".repeat(40), fast_mlsirm_artifact_sha256: "d".repeat(64),
          compute_backend_code: "rust_gpu", precision_code: "f64", membership_fingerprint_sha256: "e".repeat(64),
        },
        topics: [{
          topic_index: 0,
          activity_intervals: [
            { state_code: "dormant", valid_from: "2026-08-01T00:00:00Z", valid_to: "2026-08-10T00:00:00Z" },
            { state_code: "reactivated", valid_from: "2026-08-10T00:00:00Z", valid_to: "2026-09-01T00:00:00Z" },
          ],
          lineage_events: [{ event_code: "birth", source_topic_index: 0, target_topic_index: null, event_time: "2026-08-01T00:00:00Z", evidence_sha256: "f".repeat(64) }],
          contexts: [
            {
              dimension_code: "business_unit", context_id: "bu-synthetic", context_label: "Synthetic Energy Division",
              influences: [{ post_id: "synthetic-post-1", occurred_at: "2026-08-12T00:00:00Z", topic_state_code: "reactivated", model_influence: 4.25, uncertainty_method_code: "posterior_interval", uncertainty_lower_value: 3.5, uncertainty_upper_value: 5, diagnostic_status_code: "accepted", membership_weight: 0.6, membership_evidence_sha256: "1".repeat(64) }],
            },
            {
              dimension_code: "team", context_id: "team-synthetic", context_label: "Synthetic Service Team",
              influences: [
                { post_id: "synthetic-post-1", occurred_at: "2026-08-12T00:00:00Z", topic_state_code: "reactivated", model_influence: 4.25, uncertainty_method_code: "posterior_interval", uncertainty_lower_value: 3.5, uncertainty_upper_value: 5, diagnostic_status_code: "accepted", membership_weight: 0.4, membership_evidence_sha256: "2".repeat(64) },
                { post_id: "synthetic-post-2", occurred_at: "2026-08-13T00:00:00Z", topic_state_code: "reactivated", model_influence: 4.25, uncertainty_method_code: "posterior_interval", uncertainty_lower_value: 3.4, uncertainty_upper_value: 5.1, diagnostic_status_code: "accepted", membership_weight: 1, membership_evidence_sha256: "3".repeat(64) },
              ],
            },
          ],
        }],
      },
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("heading", { name: "시간 흐름별 주제 영향도" })).toBeVisible();
    await expect(canvas.getByText(/휴면 \/ 재활성/)).toBeVisible();
    await expect(canvas.getAllByText("4.25")).toHaveLength(3);
    await expect(canvas.getByText(/영향도와 불확실성을 함께 비교하고 같은 값은 동점으로 확인하세요/)).toBeVisible();
  },
};

export const NarrowViewport: Story = { ...EvidenceReady, parameters: { viewport: { defaultViewport: "mobile1" } } };

export const ExternalInformationEmpty: Story = {
  args: {
    data: { ...EvidenceReady.args!.data!, cases: EvidenceReady.args!.data!.cases.filter((item) => item.case_kind_code !== "external_information") },
    externalOnly: true,
    onOpenPost: () => undefined,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("status")).toHaveTextContent("분류된 외부 정보가 없습니다");
    await expect(canvas.queryByText("전체 글")).not.toBeInTheDocument();
    await expect(canvas.queryByText("분류 사건")).not.toBeInTheDocument();
    await expect(canvas.queryByText("분석 대기")).not.toBeInTheDocument();
    await expect(canvas.queryByText("분석 실패")).not.toBeInTheDocument();
  },
};

export const RequiredFactMissing: Story = {
  args: {
    data: { ...EvidenceReady.args!.data!, cases: [EvidenceReady.args!.data!.cases[0]] },
    onOpenPost: () => undefined,
  },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText(/수주 Pool: 관련 근거를 찾으면 자동으로 다시 분석합니다. 이후 결과를 다시 확인하세요/)).toBeVisible();
  },
};

export const AnalysisPendingAndMissingEvidence: Story = {
  args: {
    data: { ...EvidenceReady.args!.data!, total_event_count: 0, pending_analysis_count: 3, cases: [] },
    onOpenPost: () => undefined,
  },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("status")).toHaveTextContent("분석 대기 건부터 처리하세요");
  },
};

export const AnalysisFailed: Story = {
  args: {
    data: { ...EvidenceReady.args!.data!, pending_analysis_count: 0, failed_analysis_count: 2, cases: [] },
    onOpenPost: () => undefined,
  },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent("재처리한 뒤 근거 누락 여부를 다시 확인하세요");
  },
};

export const LoadError: Story = {
  args: EvidenceReady.args,
  render: () => <OperationsDashboard accessToken="synthetic-token" onOpenPost={() => undefined} />,
  beforeEach: () => {
    const fetchBeforeStory = globalThis.fetch;
    globalThis.fetch = async () => { throw new Error("synthetic transport failure"); };
    return () => { globalThis.fetch = fetchBeforeStory; };
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.findByRole("alert")).resolves.toHaveTextContent("불러오지 못했습니다");
    await expect(canvas.getByRole("button", { name: "다시 시도" })).toBeVisible();
  },
};

export const ConcurrentLoading: Story = {
  args: EvidenceReady.args,
  render: () => <OperationsDashboard accessToken="synthetic-token" onOpenPost={() => undefined} />,
  beforeEach: () => {
    const fetchBeforeStory = globalThis.fetch;
    globalThis.fetch = async () => new Promise(() => undefined);
    return () => { globalThis.fetch = fetchBeforeStory; };
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getAllByRole("status")).toHaveLength(1);
    await expect(canvas.getByRole("status")).toHaveTextContent("Loading voice evidence");
  },
};

export const VoiceSummaryLoadError: Story = {
  args: EvidenceReady.args,
  render: () => <OperationsDashboard accessToken="synthetic-token" onOpenPost={() => undefined} />,
  beforeEach: () => {
    const fetchBeforeStory = globalThis.fetch;
    globalThis.fetch = async (input) => {
      if (String(input).includes("/api/dashboard")) {
        return new Response(JSON.stringify(EvidenceReady.args!.data!), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      throw new Error("synthetic voice-summary transport failure");
    };
    return () => { globalThis.fetch = fetchBeforeStory; };
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.findByRole("alert")).resolves.toHaveTextContent("Voice evidence could not be loaded");
    await expect(canvas.getByRole("button", { name: "Retry voice evidence" })).toBeVisible();
  },
};
