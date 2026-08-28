import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { LeftoverPair } from "../api";
import { LeftoverMapPlot } from "./LeftoverMapPlot";

const PAIRS: LeftoverPair[] = [
  {
    pair_kind: "closest",
    post_id: "post-demo-public",
    post_title: "Public post",
    criterion_code: "sales_lead_quality",
    leftover_distance: 0.12,
    leftover_residual: 0.4,
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
    leftover_map_person_axis_1: 0.9,
    leftover_map_person_axis_2: 0.8,
    leftover_map_item_axis_1: -0.7,
    leftover_map_item_axis_2: -0.4,
  },
];

function criterionLabel(code: string): string {
  return code === "sales_lead_quality" ? "sales-lead" : "negative";
}

describe("LeftoverMapPlot", () => {
  it("draws persisted leftover-map coordinates so a post marker opens that post", async () => {
    const onSelectPost = vi.fn();
    render(
      <LeftoverMapPlot pairs={PAIRS} criterionLabel={criterionLabel} onSelectPost={onSelectPost} />,
    );

    expect(screen.getByLabelText("Leftover-map graphic display")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Leftover map after IRT main effects. Click a post marker to open that post. The plot does not invent a leftover score.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Post ξ")).toBeInTheDocument();
    expect(screen.getByText("Criterion ζ")).toBeInTheDocument();

    const postMarker = screen.getByRole("button", {
      name: "Open leftover-map post Public post at ξ (+0.50, +0.10)",
    });
    await userEvent.click(postMarker);
    expect(onSelectPost).toHaveBeenCalledWith(
      expect.objectContaining({
        pair_kind: "closest",
        post_id: "post-demo-public",
        criterion_code: "sales_lead_quality",
      }),
    );
  });

  it("omits the plot when leftover-map coordinates are missing", () => {
    const { container } = render(
      <LeftoverMapPlot
        pairs={[
          {
            pair_kind: "closest",
            post_id: "post-demo-public",
            post_title: "Public post",
            criterion_code: "sales_lead_quality",
            leftover_distance: 0.12,
            leftover_residual: 0.4,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("plots a rank-0 origin without inventing leftover structure", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            pair_kind: "closest",
            post_id: "post-demo-public",
            post_title: "Public post",
            criterion_code: "sales_lead_quality",
            leftover_distance: 0,
            leftover_residual: 0,
            leftover_map_rank: 0,
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Open leftover-map post Public post at ξ (0.00, 0.00)" }),
    ).toBeInTheDocument();
  });
});
