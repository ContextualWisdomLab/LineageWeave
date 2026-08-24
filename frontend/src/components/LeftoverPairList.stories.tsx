import type { Meta, StoryObj } from "@storybook/react-vite";
import { LeftoverPairList } from "./LeftoverPairList";

const meta = {
  title: "Reports/LeftoverPairList",
  component: LeftoverPairList,
  args: {
    criterionLabel: (code: string) =>
      code === "sales_lead_quality" ? "sales-lead" : "negative",
    onSelectPost: () => undefined,
    pairs: [
      {
        pair_kind: "closest",
        post_id: "post-demo-public",
        post_title: "Public post",
        criterion_code: "sales_lead_quality",
        leftover_distance: 0.12,
        leftover_residual: 0.4,
        observed_response: 2.4,
        expected_response: 2.0,
        leftover_map_rank: 1,
        leftover_map_reconstruction: 0.4,
      },
      {
        pair_kind: "farthest",
        post_id: "post-demo-spec",
        post_title: "Specification revision requested",
        criterion_code: "negative_sentiment",
        leftover_distance: 1.84,
        leftover_residual: -1.1,
        observed_response: 0.9,
        expected_response: 2.0,
        leftover_map_rank: 1,
        leftover_map_reconstruction: -1.1,
      },
    ],
  },
} satisfies Meta<typeof LeftoverPairList>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ClosestAndFarthest: Story = {};

export const Empty: Story = {
  args: {
    pairs: [],
  },
};
