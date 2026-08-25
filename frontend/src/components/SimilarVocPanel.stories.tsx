import type { Meta, StoryObj } from "@storybook/react";
import { SimilarVocPanel } from "./SimilarVocPanel";

const meta = { title: "Post/Similar VOC", component: SimilarVocPanel } satisfies Meta<typeof SimilarVocPanel>;
export default meta;
type Story = StoryObj<typeof meta>;

export const WithActionHistory: Story = { args: { items: [{
  post_id: "synthetic-post-2", post_title: "합성 과거 VOC", issue_summary: "동일 씰 고장 유형",
  candidate_evidence_text: "시험 중 씰 누설이 확인되었습니다.", customer_cohort_text: "합성 고객군 A",
  action_history: ["가스켓을 교체하고 압력을 재검증했습니다."], fused_rank: 1,
}], onOpenPost: () => undefined } };
export const Empty: Story = { args: { items: [], onOpenPost: () => undefined } };
