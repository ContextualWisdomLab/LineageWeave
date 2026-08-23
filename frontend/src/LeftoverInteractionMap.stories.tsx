import type { Meta, StoryObj } from "@storybook/react-vite";
import { LeftoverInteractionMap } from "./LeftoverInteractionMap";

const itemLabel = (code: string) =>
  code === "sales_lead_specificity" ? "sales-lead" : code.replaceAll("_", " ");

const meta = {
  title: "Reports/LeftoverInteractionMap",
  component: LeftoverInteractionMap,
  args: {
    persons: [
      { post_id: "post-1", post_title: "Public post", axis_one: -0.5, axis_two: 0.1 },
      {
        post_id: "post-2",
        post_title: "Specification revision requested",
        axis_one: 0.8,
        axis_two: -0.4,
      },
    ],
    items: [
      { criterion_code: "sales_lead_specificity", axis_one: -0.4, axis_two: 0.05 },
      { criterion_code: "general_sentiment_negative", axis_one: 1.2, axis_two: -0.9 },
      { criterion_code: "general_sentiment_positive", axis_one: 0.1, axis_two: 0.7 },
    ],
    pairs: [
      {
        pair_kind: "closest",
        post_id: "post-1",
        post_title: "Public post",
        criterion_code: "sales_lead_specificity",
        leftover_distance: 0.12,
        leftover_residual: 0.4,
      },
      {
        pair_kind: "farthest",
        post_id: "post-2",
        post_title: "Specification revision requested",
        criterion_code: "general_sentiment_negative",
        leftover_distance: 1.84,
        leftover_residual: -1.1,
      },
    ],
    itemLabel,
    onSelectPost: () => undefined,
  },
} satisfies Meta<typeof LeftoverInteractionMap>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ClosestFarthest: Story = {};

export const CriterionClick: Story = {
  args: {
    items: [{ criterion_code: "sales_lead_specificity", axis_one: -0.4, axis_two: 0.05 }],
    pairs: [
      {
        pair_kind: "closest",
        post_id: "post-1",
        post_title: "Public post",
        criterion_code: "sales_lead_specificity",
        leftover_distance: 0.12,
        leftover_residual: 0.4,
      },
    ],
  },
};

export const OriginPad: Story = {
  args: {
    persons: [{ post_id: "post-1", post_title: "Public post", axis_one: 0, axis_two: 0 }],
    items: [{ criterion_code: "sales_lead_specificity", axis_one: 0, axis_two: 0 }],
    pairs: [],
  },
};
