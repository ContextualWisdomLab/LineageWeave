import type { Meta, StoryObj } from "@storybook/react";
import { SimilarVocPanel } from "./SimilarVocPanel";

const meta = { title: "Post/Similar VOC", component: SimilarVocPanel } satisfies Meta<typeof SimilarVocPanel>;
export default meta;
type Story = StoryObj<typeof meta>;

export const WithActionHistory: Story = { args: { items: [{
  post_id: "synthetic-post-2", post_title: "합성 과거 VOC", issue_summary: "동일 씰 고장 유형",
  focal_evidence_text: "합성 고객군 A의 인수 검사 중 씰 누설이 확인되었습니다.",
  candidate_evidence_text: "합성 고객군 A의 시험 중 씰 누설이 확인되었습니다.", customer_cohort_text: "합성 고객군 A",
  action_history: ["가스켓을 교체하고 압력을 재검증했습니다."], occurred_at: "2026-08-20T09:00:00Z",
}], onOpenPost: () => undefined } };
export const Empty: Story = { args: { items: [], onOpenPost: () => undefined } };
export const Loading: Story = { args: { items: null, onOpenPost: () => undefined } };
export const Unavailable: Story = { args: { items: [], error: "유사 VOC 판정을 사용할 수 없습니다. 잠시 후 다시 확인하세요.", onOpenPost: () => undefined } };
