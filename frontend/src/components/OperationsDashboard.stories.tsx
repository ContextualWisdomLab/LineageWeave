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
      failed_analysis_count: 0,
      cases: [
        { post_id: "synthetic-post-1", case_kind_code: "claim_investigation", case_kind_label: "클레임 원인 역추적", project_name: "Synthetic Transformer Renewal", summary_text: "사양 변경 이후 원인 수주와 Pool을 확인", evidence_text: "Revision B originated in order SO-100 from pool SP-20.", evidence_post_id: "synthetic-post-1", occurred_at: "2026-08-04T00:00:00Z", facts: [{ fact_type_code: "originating_order", fact_type_label: "원인 수주", value_text: "SO-100 · SP-20", evidence_text: "order SO-100 from pool SP-20", evidence_post_id: "synthetic-post-1" }], missing_facts: [{ fact_type_code: "order", fact_type_label: "발생 수주" }, { fact_type_code: "specification_change", fact_type_label: "사양 변경" }, { fact_type_code: "sales_pool", fact_type_label: "수주 Pool" }] },
        { post_id: "synthetic-post-2", case_kind_code: "rebid_handover", case_kind_label: "재입찰 · 인수인계", project_name: "Synthetic Transformer Renewal", summary_text: "담당자 교체 전 협의와 후속 결정을 연결", evidence_text: "The account owner and design lead agreed to submit the revised proposal.", evidence_post_id: "synthetic-post-2", occurred_at: "2026-08-11T00:00:00Z", facts: [{ fact_type_code: "decision", fact_type_label: "이어진 결정", value_text: "수정 제안 제출", evidence_text: "submit the revised proposal", evidence_post_id: "synthetic-post-2" }], missing_facts: [{ fact_type_code: "discussion", fact_type_label: "협의 내용" }, { fact_type_code: "counterparty", fact_type_label: "협의 상대" }, { fact_type_code: "our_owner", fact_type_label: "우리측 담당자" }] },
        { post_id: "synthetic-post-3", case_kind_code: "external_information", case_kind_label: "외부 정보", project_name: "Synthetic Transformer Renewal", summary_text: "시장 공고를 영업 기회와 연결", evidence_text: "The public procurement notice opened on August 15.", evidence_post_id: "synthetic-post-3", occurred_at: "2026-08-15T00:00:00Z", facts: [{ fact_type_code: "external_relation", fact_type_label: "업무 관계", value_text: "갱신 제안 준비", evidence_text: "procurement notice", evidence_post_id: "synthetic-post-3" }], missing_facts: [] },
        { post_id: "synthetic-post-4", case_kind_code: "repeat_issue", case_kind_label: "반복 이슈 반영", project_name: "Synthetic Transformer Renewal", summary_text: "동일 유형 이슈를 설계 개선으로 환류", evidence_text: "The same enclosure issue recurred after Revision B.", evidence_post_id: "synthetic-post-4", occurred_at: "2026-08-18T00:00:00Z", facts: [{ fact_type_code: "improvement_action", fact_type_label: "개선 과제", value_text: "표준 사양 개정", evidence_text: "Update the standard enclosure specification.", evidence_post_id: "synthetic-post-4" }], missing_facts: [{ fact_type_code: "issue_pattern", fact_type_label: "반복 유형" }] },
      ],
    },
    onOpenPost: () => undefined,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("9건 · 22.5%")).toBeInTheDocument();
    await expect(canvas.getByText("7 Event · 5글")).toBeVisible();
    await expect(canvas.getAllByRole("button", { name: "분류 근거 글 열기" })[0]).toBeVisible();
  },
};

export const NarrowViewport: Story = { ...EvidenceReady, parameters: { viewport: { defaultViewport: "mobile1" } } };

export const RequiredFactMissing: Story = {
  args: {
    data: { ...EvidenceReady.args!.data!, cases: [EvidenceReady.args!.data!.cases[0]] },
    onOpenPost: () => undefined,
  },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText(/수주 Pool: 권한 범위 내 근거가 없습니다/)).toBeVisible();
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
