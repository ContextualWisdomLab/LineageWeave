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
    leftover_map_reconstruction: 0.248,
    leftover_map_explained_share: 0.76,
    leftover_map_unexplained_share: 0.02,
    leftover_map_cross_share: 0.12,
    leftover_map_unexplained: 0.05,
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
    leftover_map_reconstruction: -0.95,
    leftover_map_explained_share: 0.6,
    leftover_map_unexplained_share: 0.05,
    leftover_map_cross_share: -0.24,
    leftover_map_unexplained: -0.25,
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
        "Leftover map after IRT main effects. Axis ticks name persisted leftover-map coordinates. Pair segments name leftover-map distance d, leftover-map reconstruction R̂, leftover-map explained leftover share e, leftover-map unexplained leftover share s, leftover-map cross share x, leftover-map unexplained leftover U, and leftover residual R. Click a post marker to open that post. The plot does not invent a leftover score.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Post ξ")).toBeInTheDocument();
    expect(screen.getByText("Criterion ζ")).toBeInTheDocument();
    expect(screen.getByText("leftover-map axis 1")).toBeInTheDocument();
    expect(screen.getByText("leftover-map axis 2")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map axis 1 tick +0.50")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map axis 2 tick −0.02")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map axis 1 tick 0.00")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 1.84")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map reconstruction R̂ +0.25")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map reconstruction R̂ −0.95")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map explained leftover share R̂²/R² 0.76")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map explained leftover share R̂²/R² 0.60")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map unexplained leftover share U²/R² 0.02")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map unexplained leftover share U²/R² 0.05")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map cross share 2R̂U/R² 0.12")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map cross share 2R̂U/R² -0.24")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map unexplained leftover U +0.05")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map unexplained leftover U −0.25")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover residual R +0.40")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover residual R −1.10")).toBeInTheDocument();

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
            leftover_map_reconstruction: 0,
            leftover_map_explained_share: 0,
            leftover_map_unexplained_share: 0,
            leftover_map_cross_share: 0,
            leftover_map_unexplained: 0,
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
          },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 0, leftover_share: 0 },
          { axis_index: 2, leftover_singular_value: 0, leftover_share: 0 },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Open leftover-map post Public post at ξ (0.00, 0.00)" }),
    ).toBeInTheDocument();
    expect(screen.getByText("leftover-map axis 1 (0%)")).toBeInTheDocument();
    expect(screen.getByText("leftover-map axis 2 (0%)")).toBeInTheDocument();
    expect(screen.getAllByLabelText("leftover-map axis 1 tick 0.00").length).toBeGreaterThan(0);
    expect(screen.queryByLabelText("leftover-map axis 1 tick +1.00")).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.00")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map reconstruction R̂ 0.00")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map explained leftover share R̂²/R² 0.00")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map unexplained leftover share U²/R² 0.00")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map cross share 2R̂U/R² 0.00")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map unexplained leftover U 0.00")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover residual R 0.00")).toBeInTheDocument();
  });

  it("captions leftover-map axes with persisted leftover-map axis share", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.getByText("leftover-map axis 1 (82%)")).toBeInTheDocument();
    expect(screen.getByText("leftover-map axis 2 (18%)")).toBeInTheDocument();
  });

  it("keeps existing leftover-map axis text when share is missing or non-finite", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: Number.NaN },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.getByText("leftover-map axis 1")).toBeInTheDocument();
    expect(screen.getByText("leftover-map axis 2")).toBeInTheDocument();
    expect(screen.queryByText(/leftover-map axis 1 \(/)).not.toBeInTheDocument();
    expect(screen.queryByText(/leftover-map axis 2 \(/)).not.toBeInTheDocument();
  });

  it("omits leftover-map distance on a pair segment when d is missing", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            pair_kind: "closest",
            post_id: "post-demo-public",
            post_title: "Public post",
            criterion_code: "sales_lead_quality",
            leftover_distance: Number.NaN,
            leftover_residual: 0.4,
            leftover_map_person_axis_1: 0.5,
            leftover_map_person_axis_2: 0.1,
            leftover_map_item_axis_1: 0.5,
            leftover_map_item_axis_2: -0.02,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText(/leftover-map distance/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map axis 1 tick +0.50")).toBeInTheDocument();
  });

  it("omits leftover-map reconstruction on a pair segment when R̂ is missing", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            pair_kind: "closest",
            post_id: "post-demo-public",
            post_title: "Public post",
            criterion_code: "sales_lead_quality",
            leftover_distance: 0.12,
            leftover_residual: 0.4,
            leftover_map_reconstruction: Number.NaN,
            leftover_map_person_axis_1: 0.5,
            leftover_map_person_axis_2: 0.1,
            leftover_map_item_axis_1: 0.5,
            leftover_map_item_axis_2: -0.02,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText(/leftover-map reconstruction/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
  });

  it("omits leftover-map explained leftover share on a pair segment when e is missing", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            pair_kind: "closest",
            post_id: "post-demo-public",
            post_title: "Public post",
            criterion_code: "sales_lead_quality",
            leftover_distance: 0.12,
            leftover_residual: 0.4,
            leftover_map_reconstruction: 0.248,
            leftover_map_explained_share: Number.NaN,
            leftover_map_person_axis_1: 0.5,
            leftover_map_person_axis_2: 0.1,
            leftover_map_item_axis_1: 0.5,
            leftover_map_item_axis_2: -0.02,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText(/leftover-map explained leftover share/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map reconstruction R̂ +0.25")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
  });

  it("omits leftover-map unexplained leftover share on a pair segment when s is missing", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            pair_kind: "closest",
            post_id: "post-demo-public",
            post_title: "Public post",
            criterion_code: "sales_lead_quality",
            leftover_distance: 0.12,
            leftover_residual: 0.4,
            leftover_map_reconstruction: 0.248,
            leftover_map_explained_share: 0.76,
            leftover_map_unexplained_share: Number.NaN,
            leftover_map_person_axis_1: 0.5,
            leftover_map_person_axis_2: 0.1,
            leftover_map_item_axis_1: 0.5,
            leftover_map_item_axis_2: -0.02,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText(/leftover-map unexplained leftover share/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map explained leftover share R̂²/R² 0.76")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map reconstruction R̂ +0.25")).toBeInTheDocument();
  });

  it("omits leftover-map cross share on a pair segment when x is missing", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            pair_kind: "closest",
            post_id: "post-demo-public",
            post_title: "Public post",
            criterion_code: "sales_lead_quality",
            leftover_distance: 0.12,
            leftover_residual: 0.4,
            leftover_map_reconstruction: 0.248,
            leftover_map_explained_share: 0.76,
            leftover_map_unexplained_share: 0.02,
            leftover_map_cross_share: Number.NaN,
            leftover_map_person_axis_1: 0.5,
            leftover_map_person_axis_2: 0.1,
            leftover_map_item_axis_1: 0.5,
            leftover_map_item_axis_2: -0.02,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText(/leftover-map cross share/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map unexplained leftover share U²/R² 0.02")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map explained leftover share R̂²/R² 0.76")).toBeInTheDocument();
  });

  it("omits leftover-map unexplained leftover on a pair segment when U is missing", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            pair_kind: "closest",
            post_id: "post-demo-public",
            post_title: "Public post",
            criterion_code: "sales_lead_quality",
            leftover_distance: 0.12,
            leftover_residual: 0.4,
            leftover_map_reconstruction: 0.248,
            leftover_map_explained_share: 0.76,
            leftover_map_unexplained_share: 0.02,
            leftover_map_cross_share: 0.12,
            leftover_map_unexplained: Number.NaN,
            leftover_map_person_axis_1: 0.5,
            leftover_map_person_axis_2: 0.1,
            leftover_map_item_axis_1: 0.5,
            leftover_map_item_axis_2: -0.02,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText(/^leftover-map unexplained leftover U/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map cross share 2R̂U/R² 0.12")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map unexplained leftover share U²/R² 0.02")).toBeInTheDocument();
  });

  it("omits leftover residual on a pair segment when R is missing", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            pair_kind: "closest",
            post_id: "post-demo-public",
            post_title: "Public post",
            criterion_code: "sales_lead_quality",
            leftover_distance: 0.12,
            leftover_residual: Number.NaN,
            leftover_map_reconstruction: 0.248,
            leftover_map_explained_share: 0.76,
            leftover_map_unexplained_share: 0.02,
            leftover_map_cross_share: 0.12,
            leftover_map_unexplained: 0.05,
            leftover_map_person_axis_1: 0.5,
            leftover_map_person_axis_2: 0.1,
            leftover_map_item_axis_1: 0.5,
            leftover_map_item_axis_2: -0.02,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText(/^leftover residual R/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map unexplained leftover U +0.05")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map cross share 2R̂U/R² 0.12")).toBeInTheDocument();
  });
});
