import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { LeftoverPairList } from "./LeftoverPairList";

const meta = {
  title: "Reports/LeftoverPairList",
  component: LeftoverPairList,
  args: {
    criterionLabel: (code: string) =>
      code === "sales_lead_quality" ? "sales-lead" : "negative",
    onSelectPost: () => undefined,
    leftoverMapAxes: [
      { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
      { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
    ],
    leftoverMapCoverage: {
      map_post_count: 2,
      scored_post_count: 3,
      map_item_count: 2,
      scored_item_count: 2,
      incomplete_post_count: 1,
      incomplete_item_count: 0,
    },
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
        leftover_map_reconstruction: 0.248,
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
        leftover_distance: 2.0,
        leftover_residual: -1.1,
        observed_response: 0.9,
        expected_response: 2.0,
        leftover_map_rank: 1,
        leftover_map_unexplained: -0.25,
        leftover_map_reconstruction: -0.95,
        leftover_map_cross_share: -0.24,
        leftover_map_unexplained_share: 0.05,
        leftover_map_explained_share: 0.60,
        leftover_map_person_axis_1: 0.9,
        leftover_map_person_axis_2: 0.8,
        leftover_map_item_axis_1: -0.7,
        leftover_map_item_axis_2: -0.4,
      },
    ],
  },
} satisfies Meta<typeof LeftoverPairList>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ClosestAndFarthest: Story = {
  args: {
    onSelectPost: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const closest = canvas.getByRole("button", {
      name: /^Closest leftover: Public post · sales-lead /,
    });
    const farthest = canvas.getByRole("button", {
      name: /^Farthest leftover: Specification revision requested · negative /,
    });

    await expect(closest).toHaveAccessibleName(/R \+0\.40/);
    await expect(closest).toHaveAccessibleName(/Y 2\.40 · E 2\.00/);
    await expect(closest).toHaveAccessibleName(/d 0\.12/);
    await expect(farthest).toHaveAccessibleName(/R −1\.10/);
    await expect(farthest).toHaveAccessibleName(/d 2\.00/);

    await userEvent.tab();
    await expect(closest).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await expect(args.onSelectPost).toHaveBeenCalledTimes(1);
    await expect(args.onSelectPost).toHaveBeenCalledWith(args.pairs[0]);

    await userEvent.tab();
    await expect(farthest).toHaveFocus();
  },
};

export const Empty: Story = {
  args: {
    pairs: [],
  },
};
