import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { OperationsDashboardView } from "./OperationsDashboard";
import "../App.css";

const meta = { title: "Workspace/OperationsDashboard", component: OperationsDashboardView, parameters: { layout: "fullscreen" } } satisfies Meta<typeof OperationsDashboardView>;
export default meta;
type Story = StoryObj<typeof meta>;

export const EvidenceReady: Story = {
  args: {
    data: {
      period_label: "2026-08-01–2026-08-25 · Event time", total_post_count: 40, total_event_count: 17,
      external_post_count: 9, external_percent: 22.5, pending_analysis_count: 3,
      cases: [{ post_id: "synthetic-post-1", case_kind_code: "repeat_issue", case_kind_label: "반복 이슈 반영", project_name: "Synthetic Transformer Renewal", summary_text: "동일 유형 이슈를 설계 개선으로 환류", evidence_text: "The same enclosure issue recurred after Revision B.", occurred_at: "2026-08-18T00:00:00Z", facts: [{ fact_type_code: "improvement_action", fact_type_label: "개선 과제", value_text: "표준 사양 개정", evidence_text: "Update the standard enclosure specification." }] }],
    },
    onOpenPost: () => undefined,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("9건 · 22.5%")).toBeInTheDocument();
    await expect(canvas.getByRole("button", { name: "근거 글 열기" })).toBeVisible();
  },
};

export const NarrowViewport: Story = { ...EvidenceReady, parameters: { viewport: { defaultViewport: "mobile1" } } };
