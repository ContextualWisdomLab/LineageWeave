import type { Meta, StoryObj } from "@storybook/react-vite";
import { GroundedQa } from "./GroundedQa";

const meta = {
  title: "Ask Agent/GroundedQa",
  component: GroundedQa,
  args: {
    onAsk: async (question: string) => ({
      question,
      slot_code: "who",
      values: ["Ada West"],
      grounded: true,
      empty_next_action: null,
    }),
  },
} satisfies Meta<typeof GroundedQa>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Ready: Story = {};

export const UnverifiedCandidates: Story = {
  args: {
    onAsk: async (question: string) => ({
      question,
      slot_code: "where",
      values: [],
      grounded: false,
      empty_next_action: "이 사건의 어디가 아직 없습니다",
      unverified_candidates: [
        {
          label: "Demo Corp parent candidate",
          evidence_url: "https://example.test/demo-corp",
          status_label: "미검증 후보",
          promote_destination: "customers",
        },
      ],
    }),
    onPromoteCandidate: () => undefined,
  },
};
