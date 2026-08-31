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
    observed_response: 2.4,
    expected_response: 2.0,
    leftover_map_reconstruction: 0.248,
    leftover_map_explained_share: 0.76,
    leftover_map_unexplained_share: 0.02,
    leftover_map_cross_share: 0.12,
    leftover_map_unexplained: 0.05,
    leftover_map_rank: 1,
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
    leftover_map_reconstruction: -0.95,
    leftover_map_explained_share: 0.6,
    leftover_map_unexplained_share: 0.05,
    leftover_map_cross_share: -0.24,
    leftover_map_unexplained: -0.25,
    leftover_map_rank: 1,
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
        "Leftover map after IRT main effects. Axis ticks name persisted leftover-map coordinates. Pair segments name leftover-map distance d, leftover-map reconstruction R̂, leftover-map explained leftover share e, leftover-map unexplained leftover share s, leftover-map cross share x, leftover-map unexplained leftover U, leftover residual R, leftover observed Y, leftover expected E, and leftover-map rank. The plot names leftover-map complete-case coverage, leftover-map item complete-case coverage, leftover-map incomplete post coverage, and leftover-map incomplete item coverage when persisted. Click a post marker to open that post. The plot does not invent a leftover score.",
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
    expect(screen.getByLabelText("leftover observed Y 2.40")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover observed Y 0.90")).toBeInTheDocument();
    expect(screen.getAllByLabelText("leftover expected E 2.00")).toHaveLength(2);
    expect(screen.getAllByLabelText("leftover-map rank rank 1")).toHaveLength(2);
    expect(screen.queryByLabelText("Leftover-map graphic coverage")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic item coverage")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic incomplete posts")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic incomplete items")).not.toBeInTheDocument();


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
            observed_response: 0,
            expected_response: 0,
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
    expect(screen.getByLabelText("leftover observed Y 0.00")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover expected E 0.00")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map rank rank 0")).toBeInTheDocument();
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

  it("omits leftover observed on a pair segment when Y is missing", () => {
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
    expect(screen.queryByLabelText(/^leftover observed Y/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover residual R +0.40")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map unexplained leftover U +0.05")).toBeInTheDocument();
  });

  it("omits leftover expected on a pair segment when E is missing", () => {
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
            observed_response: 2.4,
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
    expect(screen.queryByLabelText(/^leftover expected E/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover observed Y 2.40")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover residual R +0.40")).toBeInTheDocument();
  });

  it("omits leftover-map rank on a pair segment when rank is missing", () => {
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
            observed_response: 2.4,
            expected_response: 2.0,
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
    expect(screen.queryByLabelText(/^leftover-map rank/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover expected E 2.00")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover observed Y 2.40")).toBeInTheDocument();
  });

  it("names persisted leftover-map complete-case coverage on the graphic without inventing a leftover score", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Leftover-map graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover-map graphic coverage")).not.toHaveTextContent(
      "Leftover map used 2 of 2 scored posts (complete-case)",
    );
  });

  it("omits leftover-map coverage on the graphic when coverage is missing or not usable", () => {
    const { rerender } = render(
      <LeftoverMapPlot pairs={PAIRS} criterionLabel={criterionLabel} onSelectPost={vi.fn()} />,
    );
    expect(screen.queryByLabelText("Leftover-map graphic coverage")).not.toBeInTheDocument();
    rerender(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapCoverage={{
          map_post_count: 4,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 0,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText("Leftover-map graphic coverage")).not.toBeInTheDocument();
    expect(screen.getAllByLabelText("leftover-map rank rank 1")).toHaveLength(2);
  });

  it("names leftover-map coverage 0 of M on a rank-0 origin when that persisted used count is a non-negative integer", () => {
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
            observed_response: 0,
            expected_response: 0,
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
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Leftover-map graphic coverage")).toHaveTextContent(
      "Leftover map used 0 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("leftover-map rank rank 0")).toBeInTheDocument();
  });

  it("names persisted leftover-map item complete-case coverage on the graphic without inventing a leftover score", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 1,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 1,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Leftover-map graphic item coverage")).toHaveTextContent(
      "Leftover map used 1 of 2 scored criteria (complete-case)",
    );
    expect(screen.getByLabelText("Leftover-map graphic item coverage")).not.toHaveTextContent(
      "Leftover map used 2 of 2 scored criteria (complete-case)",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 1 incomplete posts",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 1 incomplete criteria",
    );
  });

  it("omits leftover-map item coverage on the graphic when item coverage is missing or not usable", () => {
    const { rerender } = render(
      <LeftoverMapPlot pairs={PAIRS} criterionLabel={criterionLabel} onSelectPost={vi.fn()} />,
    );
    expect(screen.queryByLabelText("Leftover-map graphic item coverage")).not.toBeInTheDocument();
    rerender(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 3,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText("Leftover-map graphic item coverage")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Leftover-map graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 1 incomplete posts",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 0 incomplete criteria",
    );
  });

  it("names leftover-map item coverage 0 of M on a rank-0 origin when that persisted used count is a non-negative integer", () => {
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
            observed_response: 0,
            expected_response: 0,
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
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Leftover-map graphic item coverage")).toHaveTextContent(
      "Leftover map used 0 of 2 scored criteria (complete-case)",
    );
    expect(screen.getByLabelText("Leftover-map graphic coverage")).toHaveTextContent(
      "Leftover map used 0 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 3 incomplete posts",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 2 incomplete criteria",
    );
  });

  it("omits leftover-map incomplete posts on the graphic when the dropped count is missing or not usable", () => {
    const { rerender } = render(
      <LeftoverMapPlot pairs={PAIRS} criterionLabel={criterionLabel} onSelectPost={vi.fn()} />,
    );
    expect(screen.queryByLabelText("Leftover-map graphic incomplete posts")).not.toBeInTheDocument();
    rerender(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 2,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText("Leftover-map graphic incomplete posts")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Leftover-map graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 0 incomplete criteria",
    );
  });

  it("names leftover-map incomplete posts 0 when that persisted dropped count is a non-negative integer", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapCoverage={{
          map_post_count: 3,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 0,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 0 incomplete posts",
    );
    expect(screen.getByLabelText("Leftover-map graphic coverage")).toHaveTextContent(
      "Leftover map used 3 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 0 incomplete criteria",
    );
  });

  it("omits leftover-map incomplete items on the graphic when the dropped count is missing or not usable", () => {
    const { rerender } = render(
      <LeftoverMapPlot pairs={PAIRS} criterionLabel={criterionLabel} onSelectPost={vi.fn()} />,
    );
    expect(screen.queryByLabelText("Leftover-map graphic incomplete items")).not.toBeInTheDocument();
    rerender(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 1,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText("Leftover-map graphic incomplete items")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Leftover-map graphic item coverage")).toHaveTextContent(
      "Leftover map used 2 of 2 scored criteria (complete-case)",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 1 incomplete posts",
    );
  });

  it("names leftover-map incomplete items 0 when that persisted dropped count is a non-negative integer", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 0 incomplete criteria",
    );
    expect(screen.getByLabelText("Leftover-map graphic item coverage")).toHaveTextContent(
      "Leftover map used 2 of 2 scored criteria (complete-case)",
    );
  });

  it("captions leftover map comparison axes with persisted leftover-map axis share", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.getByLabelText("Leftover map comparison graphic")).toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic display")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Leftover map comparison graphic of already-named coordinates. Click a post marker to open that post. The plot does not invent a leftover score.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 2 (18%)")).toBeInTheDocument();
    expect(screen.queryByText("leftover-map axis 1 (82%)")).not.toBeInTheDocument();
    expect(screen.queryByText("leftover-map axis 2 (18%)")).not.toBeInTheDocument();
  });

  it("keeps leftover map comparison axis text when share is missing or non-finite", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: Number.NaN },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.getByText("leftover map comparison axis 1")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 2")).toBeInTheDocument();
    expect(screen.queryByText(/leftover map comparison axis 1 \(/)).not.toBeInTheDocument();
    expect(screen.queryByText(/leftover map comparison axis 2 \(/)).not.toBeInTheDocument();
    expect(screen.queryByText("leftover-map axis 1")).not.toBeInTheDocument();
    expect(screen.queryByText("leftover-map axis 2")).not.toBeInTheDocument();
  });

  it("names rank-0 zero leftover-map axis share on the comparison graphic", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIRS[0],
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
        variant="comparison"
      />,
    );
    expect(screen.getByText("leftover map comparison axis 1 (0%)")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 2 (0%)")).toBeInTheDocument();
  });

  it("names leftover-map coverage on the comparison graphic with a distinct accessible name", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic item coverage")).toHaveTextContent(
      "Leftover map used 2 of 2 scored criteria (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 1 incomplete posts",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 0 incomplete criteria",
    );
    expect(screen.queryByLabelText("Leftover-map graphic coverage")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison coverage")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic item coverage")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison item coverage")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic incomplete posts")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison incomplete posts")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic incomplete items")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison incomplete items")).not.toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 2 (18%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic coverage when coverage is missing or not usable", () => {
    const { rerender } = render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.queryByLabelText("Leftover map comparison graphic coverage")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
    rerender(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 4,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 0,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.queryByLabelText("Leftover map comparison graphic coverage")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic item coverage")).toHaveTextContent(
      "Leftover map used 2 of 2 scored criteria (complete-case)",
    );
    expect(screen.queryByLabelText("Leftover-map graphic coverage")).not.toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic item coverage when item coverage is missing or not usable", () => {
    const { rerender } = render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 3,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.queryByLabelText("Leftover map comparison graphic item coverage")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic item coverage")).not.toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
    rerender(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: -1,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.queryByLabelText("Leftover map comparison graphic item coverage")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic item coverage")).not.toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic incomplete posts when incomplete post coverage is missing or not usable", () => {
    const { rerender } = render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 2,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic item coverage")).toHaveTextContent(
      "Leftover map used 2 of 2 scored criteria (complete-case)",
    );
    expect(screen.queryByLabelText("Leftover map comparison graphic incomplete posts")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic incomplete posts")).not.toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
    rerender(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: -1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.queryByLabelText("Leftover map comparison graphic incomplete posts")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic incomplete posts")).not.toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic incomplete items when incomplete item coverage is missing or not usable", () => {
    const { rerender } = render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 1,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic item coverage")).toHaveTextContent(
      "Leftover map used 2 of 2 scored criteria (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 1 incomplete posts",
    );
    expect(screen.queryByLabelText("Leftover map comparison graphic incomplete items")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic incomplete items")).not.toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
    rerender(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: -1,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 1 incomplete posts",
    );
    expect(screen.queryByLabelText("Leftover map comparison graphic incomplete items")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic incomplete items")).not.toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("names leftover-map comparison graphic coverage 0 of M on a rank-0 origin when that persisted used count is a non-negative integer", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
            leftover_map_rank: 0,
            leftover_distance: 0,
            leftover_residual: 0,
            leftover_map_reconstruction: 0,
          },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 0, leftover_share: 0 },
          { axis_index: 2, leftover_singular_value: 0, leftover_share: 0 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 0 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic item coverage")).toHaveTextContent(
      "Leftover map used 0 of 2 scored criteria (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 3 incomplete posts",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 2 incomplete criteria",
    );
    expect(screen.queryByLabelText("Leftover-map graphic coverage")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic item coverage")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic incomplete posts")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover-map graphic incomplete items")).not.toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (0%)")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 2 (0%)")).toBeInTheDocument();
  });

  it("names leftover-map reconstruction on the comparison graphic with a distinct accessible name", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toHaveTextContent("R̂ +0.25");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ −0.95"),
    ).toHaveTextContent("R̂ −0.95");
    expect(screen.queryByLabelText("leftover-map reconstruction R̂ +0.25")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("leftover-map reconstruction R̂ −0.95")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison reconstruction")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 0 incomplete criteria",
    );
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic reconstruction when R̂ is missing or not usable", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          { ...PAIRS[0], leftover_map_reconstruction: null },
          { ...PAIRS[1], leftover_map_reconstruction: Number.NaN },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.queryByLabelText(/leftover map comparison graphic reconstruction/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/leftover-map reconstruction/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 1.84")).toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("names rank-0 origin reconstruction on the comparison graphic when that persisted value is finite", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
            leftover_map_rank: 0,
            leftover_distance: 0,
            leftover_residual: 0,
            leftover_map_reconstruction: 0,
          },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 0, leftover_share: 0 },
          { axis_index: 2, leftover_singular_value: 0, leftover_share: 0 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ 0.00"),
    ).toHaveTextContent("R̂ 0.00");
    expect(screen.queryByLabelText("leftover-map reconstruction R̂ 0.00")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 0 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (0%)")).toBeInTheDocument();
  });

  it("names leftover-map explained leftover share on the comparison graphic with a distinct accessible name", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.76"),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.60"),
    ).toHaveTextContent("R̂²/R² 0.60");
    expect(screen.queryByLabelText("leftover-map explained leftover share R̂²/R² 0.76")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("leftover-map explained leftover share R̂²/R² 0.60")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison explained leftover share")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toHaveTextContent("R̂ +0.25");
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic explained leftover share when e is missing or not usable", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          { ...PAIRS[0], leftover_map_explained_share: null },
          { ...PAIRS[1], leftover_map_explained_share: Number.NaN },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.queryByLabelText(/leftover map comparison graphic explained leftover share/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/leftover-map explained leftover share/)).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 1.84")).toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("names rank-0 origin explained leftover share on the comparison graphic when that persisted value is finite", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
            leftover_map_rank: 0,
            leftover_distance: 0,
            leftover_residual: 0,
            leftover_map_reconstruction: 0,
            leftover_map_explained_share: 0,
          },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 0, leftover_share: 0 },
          { axis_index: 2, leftover_singular_value: 0, leftover_share: 0 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.00"),
    ).toHaveTextContent("R̂²/R² 0.00");
    expect(screen.queryByLabelText("leftover-map explained leftover share R̂²/R² 0.00")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ 0.00"),
    ).toHaveTextContent("R̂ 0.00");
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 0 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (0%)")).toBeInTheDocument();
  });

  it("names leftover-map unexplained leftover share on the comparison graphic with a distinct accessible name", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.02"),
    ).toHaveTextContent("U²/R² 0.02");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.05"),
    ).toHaveTextContent("U²/R² 0.05");
    expect(screen.queryByLabelText("leftover-map unexplained leftover share U²/R² 0.02")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("leftover-map unexplained leftover share U²/R² 0.05")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison unexplained leftover share")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.76"),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toHaveTextContent("R̂ +0.25");
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic unexplained leftover share when s is missing or not usable", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          { ...PAIRS[0], leftover_map_unexplained_share: null },
          { ...PAIRS[1], leftover_map_unexplained_share: Number.NaN },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.queryByLabelText(/leftover map comparison graphic unexplained leftover share/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/leftover-map unexplained leftover share/)).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.76"),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 1.84")).toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("names rank-0 origin unexplained leftover share on the comparison graphic when that persisted value is finite", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
            leftover_map_rank: 0,
            leftover_distance: 0,
            leftover_residual: 0,
            leftover_map_reconstruction: 0,
            leftover_map_explained_share: 0,
            leftover_map_unexplained_share: 0,
          },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 0, leftover_share: 0 },
          { axis_index: 2, leftover_singular_value: 0, leftover_share: 0 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.00"),
    ).toHaveTextContent("U²/R² 0.00");
    expect(screen.queryByLabelText("leftover-map unexplained leftover share U²/R² 0.00")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.00"),
    ).toHaveTextContent("R̂²/R² 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ 0.00"),
    ).toHaveTextContent("R̂ 0.00");
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 0 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (0%)")).toBeInTheDocument();
  });

  it("names leftover-map cross share on the comparison graphic with a distinct accessible name", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic cross share 2R̂U/R² 0.12"),
    ).toHaveTextContent("2R̂U/R² 0.12");
    expect(
      screen.getByLabelText("leftover map comparison graphic cross share 2R̂U/R² -0.24"),
    ).toHaveTextContent("2R̂U/R² -0.24");
    expect(screen.queryByLabelText("leftover-map cross share 2R̂U/R² 0.12")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("leftover-map cross share 2R̂U/R² -0.24")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison cross share")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.02"),
    ).toHaveTextContent("U²/R² 0.02");
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.76"),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toHaveTextContent("R̂ +0.25");
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic cross share when x is missing or not usable", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          { ...PAIRS[0], leftover_map_cross_share: null },
          { ...PAIRS[1], leftover_map_cross_share: Number.NaN },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.queryByLabelText(/leftover map comparison graphic cross share/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/leftover-map cross share/)).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.02"),
    ).toHaveTextContent("U²/R² 0.02");
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.76"),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 1.84")).toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("names rank-0 origin leftover-map cross share on the comparison graphic when that persisted value is finite", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
            leftover_map_rank: 0,
            leftover_distance: 0,
            leftover_residual: 0,
            leftover_map_reconstruction: 0,
            leftover_map_explained_share: 0,
            leftover_map_unexplained_share: 0,
            leftover_map_cross_share: 0,
          },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 0, leftover_share: 0 },
          { axis_index: 2, leftover_singular_value: 0, leftover_share: 0 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic cross share 2R̂U/R² 0.00"),
    ).toHaveTextContent("2R̂U/R² 0.00");
    expect(screen.queryByLabelText("leftover-map cross share 2R̂U/R² 0.00")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.00"),
    ).toHaveTextContent("U²/R² 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.00"),
    ).toHaveTextContent("R̂²/R² 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ 0.00"),
    ).toHaveTextContent("R̂ 0.00");
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 0 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (0%)")).toBeInTheDocument();
  });

  it("names leftover-map unexplained leftover on the comparison graphic with a distinct accessible name", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover U +0.05"),
    ).toHaveTextContent("U +0.05");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover U −0.25"),
    ).toHaveTextContent("U −0.25");
    expect(screen.queryByLabelText("leftover-map unexplained leftover U +0.05")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("leftover-map unexplained leftover U −0.25")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison unexplained leftover")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic cross share 2R̂U/R² 0.12"),
    ).toHaveTextContent("2R̂U/R² 0.12");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.02"),
    ).toHaveTextContent("U²/R² 0.02");
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.76"),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toHaveTextContent("R̂ +0.25");
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic unexplained leftover when U is missing or not usable", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          { ...PAIRS[0], leftover_map_unexplained: null },
          { ...PAIRS[1], leftover_map_unexplained: Number.NaN },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.queryByLabelText(/leftover map comparison graphic unexplained leftover U/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^leftover-map unexplained leftover U/)).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic cross share 2R̂U/R² 0.12"),
    ).toHaveTextContent("2R̂U/R² 0.12");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.02"),
    ).toHaveTextContent("U²/R² 0.02");
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.76"),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 1.84")).toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("names rank-0 origin leftover-map unexplained leftover on the comparison graphic when that persisted value is finite", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
            leftover_map_rank: 0,
            leftover_distance: 0,
            leftover_residual: 0,
            leftover_map_reconstruction: 0,
            leftover_map_explained_share: 0,
            leftover_map_unexplained_share: 0,
            leftover_map_cross_share: 0,
            leftover_map_unexplained: 0,
          },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 0, leftover_share: 0 },
          { axis_index: 2, leftover_singular_value: 0, leftover_share: 0 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover U 0.00"),
    ).toHaveTextContent("U 0.00");
    expect(screen.queryByLabelText("leftover-map unexplained leftover U 0.00")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic cross share 2R̂U/R² 0.00"),
    ).toHaveTextContent("2R̂U/R² 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.00"),
    ).toHaveTextContent("U²/R² 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.00"),
    ).toHaveTextContent("R̂²/R² 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ 0.00"),
    ).toHaveTextContent("R̂ 0.00");
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 0 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (0%)")).toBeInTheDocument();
  });

  it("names leftover residual on the comparison graphic with a distinct accessible name", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover residual R +0.40"),
    ).toHaveTextContent("R +0.40");
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover residual R −1.10"),
    ).toHaveTextContent("R −1.10");
    expect(screen.queryByLabelText("leftover residual R +0.40")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("leftover residual R −1.10")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison residual")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover U +0.05"),
    ).toHaveTextContent("U +0.05");
    expect(
      screen.getByLabelText("leftover map comparison graphic cross share 2R̂U/R² 0.12"),
    ).toHaveTextContent("2R̂U/R² 0.12");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.02"),
    ).toHaveTextContent("U²/R² 0.02");
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.76"),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toHaveTextContent("R̂ +0.25");
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic leftover residual when R is missing or not usable", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          { ...PAIRS[0], leftover_residual: Number.NaN },
          { ...PAIRS[1], leftover_residual: Number.POSITIVE_INFINITY },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.queryByLabelText(/leftover map comparison graphic leftover residual R/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^leftover residual R/)).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover U +0.05"),
    ).toHaveTextContent("U +0.05");
    expect(
      screen.getByLabelText("leftover map comparison graphic cross share 2R̂U/R² 0.12"),
    ).toHaveTextContent("2R̂U/R² 0.12");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.02"),
    ).toHaveTextContent("U²/R² 0.02");
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.76"),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 1.84")).toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("names rank-0 origin leftover residual on the comparison graphic when that persisted value is finite", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
            leftover_map_rank: 0,
            leftover_distance: 0,
            leftover_residual: 0,
            leftover_map_reconstruction: 0,
            leftover_map_explained_share: 0,
            leftover_map_unexplained_share: 0,
            leftover_map_cross_share: 0,
            leftover_map_unexplained: 0,
          },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 0, leftover_share: 0 },
          { axis_index: 2, leftover_singular_value: 0, leftover_share: 0 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover residual R 0.00"),
    ).toHaveTextContent("R 0.00");
    expect(screen.queryByLabelText("leftover residual R 0.00")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover U 0.00"),
    ).toHaveTextContent("U 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic cross share 2R̂U/R² 0.00"),
    ).toHaveTextContent("2R̂U/R² 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover share U²/R² 0.00"),
    ).toHaveTextContent("U²/R² 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic explained leftover share R̂²/R² 0.00"),
    ).toHaveTextContent("R̂²/R² 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ 0.00"),
    ).toHaveTextContent("R̂ 0.00");
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 0 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (0%)")).toBeInTheDocument();
  });

  it("names leftover observed on the comparison graphic with a distinct accessible name", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover observed Y 2.40"),
    ).toHaveTextContent("Y 2.40");
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover observed Y 0.90"),
    ).toHaveTextContent("Y 0.90");
    expect(screen.queryByLabelText("leftover observed Y 2.40")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("leftover observed Y 0.90")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison observed")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover residual R +0.40"),
    ).toHaveTextContent("R +0.40");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover U +0.05"),
    ).toHaveTextContent("U +0.05");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toHaveTextContent("R̂ +0.25");
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic leftover observed when Y is missing or not usable", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          { ...PAIRS[0], observed_response: Number.NaN },
          { ...PAIRS[1], observed_response: Number.POSITIVE_INFINITY },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.queryByLabelText(/leftover map comparison graphic leftover observed Y/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^leftover observed Y/)).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover residual R +0.40"),
    ).toHaveTextContent("R +0.40");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover U +0.05"),
    ).toHaveTextContent("U +0.05");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ +0.25"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("names rank-0 origin leftover observed on the comparison graphic when that persisted value is finite", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
            leftover_map_rank: 0,
            leftover_distance: 0,
            leftover_residual: 0,
            leftover_map_reconstruction: 0,
            leftover_map_explained_share: 0,
            leftover_map_unexplained_share: 0,
            leftover_map_cross_share: 0,
            leftover_map_unexplained: 0,
            observed_response: 0,
          },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 0, leftover_share: 0 },
          { axis_index: 2, leftover_singular_value: 0, leftover_share: 0 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover observed Y 0.00"),
    ).toHaveTextContent("Y 0.00");
    expect(screen.queryByLabelText("leftover observed Y 0.00")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover residual R 0.00"),
    ).toHaveTextContent("R 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic unexplained leftover U 0.00"),
    ).toHaveTextContent("U 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic reconstruction R̂ 0.00"),
    ).toHaveTextContent("R̂ 0.00");
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 0 of 3 scored posts (complete-case)",
    );
    expect(screen.getByText("leftover map comparison axis 1 (0%)")).toBeInTheDocument();
  });

  it("names leftover expected on the comparison graphic with a distinct accessible name", () => {
    render(
      <LeftoverMapPlot
        pairs={PAIRS}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getAllByLabelText("leftover map comparison graphic leftover expected E 2.00"),
    ).toHaveLength(2);
    expect(screen.queryByLabelText("leftover expected E 2.00")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Leftover map comparison expected")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover observed Y 2.40"),
    ).toHaveTextContent("Y 2.40");
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover residual R +0.40"),
    ).toHaveTextContent("R +0.40");
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("omits leftover-map comparison graphic leftover expected when E is missing or not usable", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          { ...PAIRS[0], expected_response: Number.NaN },
          { ...PAIRS[1], expected_response: Number.POSITIVE_INFINITY },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 1.84, leftover_share: 0.82 },
          { axis_index: 2, leftover_singular_value: 0.86, leftover_share: 0.18 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 2,
          scored_post_count: 3,
          map_item_count: 2,
          scored_item_count: 2,
          incomplete_post_count: 1,
          incomplete_item_count: 0,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(screen.queryByLabelText(/leftover map comparison graphic leftover expected E/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^leftover expected E/)).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover observed Y 2.40"),
    ).toHaveTextContent("Y 2.40");
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover residual R +0.40"),
    ).toHaveTextContent("R +0.40");
    expect(screen.getByLabelText("leftover-map distance d 0.12")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison axis 1 (82%)")).toBeInTheDocument();
  });

  it("names rank-0 origin leftover expected on the comparison graphic when that persisted value is finite", () => {
    render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_person_axis_1: 0,
            leftover_map_person_axis_2: 0,
            leftover_map_item_axis_1: 0,
            leftover_map_item_axis_2: 0,
            leftover_map_rank: 0,
            leftover_distance: 0,
            leftover_residual: 0,
            leftover_map_reconstruction: 0,
            leftover_map_explained_share: 0,
            leftover_map_unexplained_share: 0,
            leftover_map_cross_share: 0,
            leftover_map_unexplained: 0,
            observed_response: 0,
            expected_response: 0,
          },
        ]}
        leftoverMapAxes={[
          { axis_index: 1, leftover_singular_value: 0, leftover_share: 0 },
          { axis_index: 2, leftover_singular_value: 0, leftover_share: 0 },
        ]}
        leftoverMapCoverage={{
          map_post_count: 0,
          scored_post_count: 3,
          map_item_count: 0,
          scored_item_count: 2,
          incomplete_post_count: 3,
          incomplete_item_count: 2,
        }}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover expected E 0.00"),
    ).toHaveTextContent("E 0.00");
    expect(screen.queryByLabelText("leftover expected E 0.00")).not.toBeInTheDocument();
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover observed Y 0.00"),
    ).toHaveTextContent("Y 0.00");
    expect(
      screen.getByLabelText("leftover map comparison graphic leftover residual R 0.00"),
    ).toHaveTextContent("R 0.00");
    expect(screen.getByText("leftover map comparison axis 1 (0%)")).toBeInTheDocument();
  });
});
