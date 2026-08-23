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
  },
  {
    pair_kind: "farthest",
    post_id: "post-demo-spec",
    post_title: "Specification revision requested",
    criterion_code: "negative_sentiment",
    leftover_distance: 1.84,
    leftover_residual: -1.1,
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
      "Leftover residual R +0.40 after IRT main effects. Open this post to read sales-lead.",
    );
    expect(closest).toHaveTextContent("R +0.40");
    expect(closest).toHaveTextContent("d 0.12");

    const farthest = screen.getByRole("button", {
      name: "Open leftover farthest pair: Specification revision requested · negative",
    });
    expect(farthest).toHaveTextContent("R −1.10");
    expect(farthest).toHaveTextContent("d 1.84");
    expect(farthest).toHaveTextContent(
      "Leftover residual R −1.10 after IRT main effects. Open this post to read negative.",
    );

    await userEvent.click(closest);
    expect(onSelectPost).toHaveBeenCalledWith("post-demo-public");
  });

  it("renders nothing when leftover pairs are missing", () => {
    const { container } = render(
      <LeftoverPairList pairs={[]} criterionLabel={criterionLabel} onSelectPost={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
