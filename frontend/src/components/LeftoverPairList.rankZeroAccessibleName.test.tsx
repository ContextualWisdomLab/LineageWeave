import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { LeftoverPair } from "../api";
import { LeftoverPairList } from "./LeftoverPairList";

const RANK_ZERO_PAIR: LeftoverPair = {
  pair_kind: "closest",
  post_id: "post-rank-zero",
  post_title: "Rank zero post",
  criterion_code: "sales_lead_quality",
  leftover_distance: 0.12,
  leftover_residual: 0.4,
  observed_response: null,
  expected_response: null,
  leftover_map_rank: 0,
};

function occurrences(value: string, token: string): number {
  return value.split(token).length - 1;
}

describe("LeftoverPairList rank-zero accessible evidence", () => {
  it("announces persisted rank 0 once when rank-zero guidance does not name the value", () => {
    render(
      <LeftoverPairList
        pairs={[RANK_ZERO_PAIR]}
        criterionLabel={() => "sales-lead"}
        onSelectPost={vi.fn()}
      />,
    );

    const action = screen.getByRole("button", {
      name: /^Closest leftover: Rank zero post · sales-lead /,
    });
    const name = action.getAttribute("aria-label") ?? "";

    expect(action).toHaveTextContent("rank 0");
    expect(action).toHaveAccessibleName(/rank 0/);
    expect(occurrences(name, "rank 0")).toBe(1);
  });
});
