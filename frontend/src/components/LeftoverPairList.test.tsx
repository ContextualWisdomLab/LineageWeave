import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { LeftoverPair } from "../api";
import { LeftoverPairList } from "./LeftoverPairList";

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
    leftover_map_rank: 1,
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
  },
];

function criterionLabel(code: string): string {
  return code === "sales_lead_quality" ? "sales-lead" : "negative";
}

describe("LeftoverPairList", () => {
  it("names leftover residual so the next click opens that post", async () => {
    const onSelectPost = vi.fn();
    render(
      <LeftoverPairList
        pairs={PAIRS}
        criterionLabel={criterionLabel}
        onSelectPost={onSelectPost}
      />,
    );

    expect(screen.getByLabelText("Leftover pairs")).toBeInTheDocument();
    const closest = screen.getByRole("button", {
      name: "Open leftover closest pair: Public post · sales-lead",
    });
    expect(closest).toHaveTextContent("Closest leftover: Public post · sales-lead");
    expect(closest).toHaveTextContent(
      "Read leftover map rank 1, observed Y 2.40, and expected E 2.00 after IRT main effects, then open this post.",
    );
    expect(closest).toHaveTextContent("R +0.40");
    expect(closest).toHaveTextContent("Y 2.40 · E 2.00");
    expect(closest).toHaveTextContent("rank 1");
    expect(closest).toHaveTextContent("d 0.12");

    const farthest = screen.getByRole("button", {
      name: "Open leftover farthest pair: Specification revision requested · negative",
    });
    expect(farthest).toHaveTextContent("R −1.10");
    expect(farthest).toHaveTextContent("Y 0.90 · E 2.00");
    expect(farthest).toHaveTextContent("rank 1");
    expect(farthest).toHaveTextContent("d 1.84");
    expect(farthest).toHaveTextContent(
      "Read leftover map rank 1, observed Y 0.90, and expected E 2.00 after IRT main effects, then open this post.",
    );

    await userEvent.click(closest);
    expect(onSelectPost).toHaveBeenCalledWith(
      expect.objectContaining({
        pair_kind: "closest",
        post_id: "post-demo-public",
        criterion_code: "sales_lead_quality",
      }),
    );
  });

  it("keeps residual guidance for an older payload without rank or Y/E", () => {
    render(
      <LeftoverPairList
        pairs={[{ ...PAIRS[0], observed_response: null, expected_response: null, leftover_map_rank: null }]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("button")).toHaveTextContent(
      "Leftover residual R +0.40 after IRT main effects. Open this post to read sales-lead.",
    );
  });

  it.each([
    [
      "rank-zero observed evidence",
      { observed_response: 1, expected_response: 1, leftover_map_rank: 0 },
      "Leftover map rank 0 means no leftover structure after IRT main effects. Read observed Y 1.00 and expected E 1.00, then open this post.",
    ],
    [
      "rank-only evidence",
      { observed_response: null, expected_response: null, leftover_map_rank: 2 },
      "Leftover map rank 2 after IRT main effects. Open this post.",
    ],
    [
      "rank-zero-only evidence",
      { observed_response: null, expected_response: null, leftover_map_rank: 0 },
      "Leftover map has no leftover structure after IRT main effects. Open this post.",
    ],
    [
      "observed and expected evidence",
      { observed_response: 2.4, expected_response: 2, leftover_map_rank: null },
      "Read observed Y 2.40 and expected E 2.00 after IRT main effects, then open this post.",
    ],
  ] as const)("selects the next action for %s", (_label, evidence, expectedAction) => {
    render(
      <LeftoverPairList
        pairs={[{ ...PAIRS[0], ...evidence }]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("button")).toHaveTextContent(expectedAction);
  });

  it("names leftover-map reconstruction so the next click opens that post", () => {
    render(
      <LeftoverPairList
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_unexplained: 0.05,
            leftover_map_reconstruction: 0.35,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );

    const closest = screen.getByRole("button");
    expect(closest).toHaveTextContent(
      "Leftover map reconstructs R̂ +0.35 after IRT main effects. Open this post to read sales-lead.",
    );
    expect(closest).toHaveTextContent("R̂ +0.35");
    expect(closest).toHaveTextContent("U +0.05");
    expect(closest).toHaveTextContent("R +0.40");
    expect(closest).toHaveTextContent("d 0.12");
  });

  it("names leftover-map explained share ahead of cross share and reconstruction", () => {
    render(
      <LeftoverPairList
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_unexplained: 0.05,
            leftover_map_cross_share: 0.12,
            leftover_map_reconstruction: 0.35,
            leftover_map_explained_share: 0.76,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );

    const closest = screen.getByRole("button");
    expect(closest).toHaveTextContent(
      "Leftover map explains 0.76 of raw residual after IRT main effects. Open this post to read sales-lead.",
    );
    expect(closest).toHaveTextContent("R̂²/R² 0.76");
    expect(closest).toHaveTextContent("2R̂U/R² 0.12");
    expect(closest).toHaveTextContent("R̂ +0.35");
    expect(closest).toHaveTextContent("U +0.05");
    expect(closest).toHaveTextContent("R +0.40");
    expect(closest).toHaveTextContent("d 0.12");
  });

  it("keeps cross-share guidance when explained share is missing", () => {
    render(
      <LeftoverPairList
        pairs={[
          {
            ...PAIRS[0],
            leftover_map_unexplained: 0.05,
            leftover_map_cross_share: 0.12,
            leftover_map_reconstruction: 0.35,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("button")).toHaveTextContent(
      "Two leftover-map axes leave identity remainder 0.12 of raw residual after IRT main effects. Open this post to read sales-lead.",
    );
  });

  it("keeps unexplained guidance when reconstruction is missing", () => {
    render(
      <LeftoverPairList
        pairs={[{ ...PAIRS[0], leftover_map_unexplained: 0.05 }]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("button")).toHaveTextContent(
      "Leftover map leaves unexplained U +0.05 after IRT main effects. Open this post to read sales-lead.",
    );
  });

  it("renders nothing when leftover pairs are missing", () => {
    const { container } = render(
      <LeftoverPairList pairs={[]} criterionLabel={criterionLabel} onSelectPost={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
