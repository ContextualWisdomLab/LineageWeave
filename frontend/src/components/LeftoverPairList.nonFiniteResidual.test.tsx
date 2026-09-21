import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { LeftoverPair } from "../api";
import { LeftoverPairList } from "./LeftoverPairList";

const NON_FINITE_RESIDUAL_PAIR: LeftoverPair = {
  pair_kind: "closest",
  post_id: "post-non-finite-residual",
  post_title: "Residual unavailable",
  criterion_code: "sales_lead_quality",
  leftover_distance: 0.12,
  leftover_residual: Number.NaN,
  observed_response: null,
  expected_response: null,
  leftover_map_rank: null,
};

describe("LeftoverPairList non-finite residual accessibility", () => {
  it("does not announce the visual residual placeholder as persisted evidence", () => {
    render(
      <LeftoverPairList
        pairs={[NON_FINITE_RESIDUAL_PAIR]}
        criterionLabel={() => "sales-lead"}
        onSelectPost={vi.fn()}
      />,
    );

    const pair = screen.getByRole("button", {
      name: /^Closest leftover: Residual unavailable · sales-lead/,
    });

    expect(pair).toHaveTextContent("R —");
    expect(pair).not.toHaveAccessibleName(/R —/);
    expect(pair).toHaveAccessibleName(/d 0\.12$/);
  });
});
