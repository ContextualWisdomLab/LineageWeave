import type { Meta, StoryObj } from "@storybook/react-vite";
import { LeftoverMapPlot } from "./LeftoverMapPlot";

const meta = {
  title: "Reports/LeftoverMapPlot",
  component: LeftoverMapPlot,
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
        leftover_map_unexplained: 0.05,
        leftover_map_reconstruction: 0.35,
        leftover_map_cross_share: 0.12,
        leftover_map_unexplained_share: 0.02,
        leftover_map_explained_share: 0.76,
        leftover_map_person_axis_1: 0.5,
        leftover_map_person_axis_2: 0.1,
        leftover_map_item_axis_1: 0.5,
        leftover_map_item_axis_2: -0.02,
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
        leftover_map_unexplained: -0.25,
        leftover_map_reconstruction: -0.85,
        leftover_map_cross_share: -0.24,
        leftover_map_unexplained_share: 0.05,
        leftover_map_explained_share: 0.6,
        leftover_map_person_axis_1: 0.9,
        leftover_map_person_axis_2: 0.8,
        leftover_map_item_axis_1: -0.7,
        leftover_map_item_axis_2: -0.4,
      },
    ],
  },
} satisfies Meta<typeof LeftoverMapPlot>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ClosestAndFarthest: Story = {};

export const RankZeroOrigin: Story = {
  args: {
    pairs: [
      {
        pair_kind: "closest",
        post_id: "post-demo-public",
        post_title: "Public post",
        criterion_code: "sales_lead_quality",
        leftover_distance: 0,
        leftover_residual: 0,
        observed_response: 1,
        expected_response: 1,
        leftover_map_rank: 0,
        leftover_map_person_axis_1: 0,
        leftover_map_person_axis_2: 0,
        leftover_map_item_axis_1: 0,
        leftover_map_item_axis_2: 0,
      },
    ],
  },
};

export const MissingCoordinates: Story = {
  args: {
    pairs: [
      {
        pair_kind: "closest",
        post_id: "post-demo-public",
        post_title: "Public post",
        criterion_code: "sales_lead_quality",
        leftover_distance: 0.12,
        leftover_residual: 0.4,
        leftover_map_rank: 1,
      },
    ],
  },
};
