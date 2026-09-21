import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { LeftoverPair } from "../api";
import { LeftoverPairList } from "./LeftoverPairList";

const BASE_PAIR: LeftoverPair = {
  pair_kind: "closest",
  post_id: "post-demo-public",
  post_title: "Public post",
  criterion_code: "sales_lead_quality",
  leftover_distance: 0.12,
  leftover_residual: 0.4,
  observed_response: 2.4,
  expected_response: 2.0,
  leftover_map_rank: 1,
};

function renderPair(pair: LeftoverPair): string {
  render(
    <LeftoverPairList
      pairs={[pair]}
      criterionLabel={() => "sales-lead"}
      onSelectPost={vi.fn()}
    />,
  );
  return screen.getByRole("button").getAttribute("aria-label") ?? "";
}

function occurrences(value: string, token: string): number {
  return value.split(token).length - 1;
}

describe("LeftoverPairList accessible evidence", () => {
  it("announces rank and observed/expected evidence once", () => {
    const name = renderPair(BASE_PAIR);

    expect(occurrences(name, "rank 1")).toBe(1);
    expect(occurrences(name, "Y 2.40")).toBe(1);
    expect(occurrences(name, "E 2.00")).toBe(1);
    expect(occurrences(name, "R +0.40")).toBe(1);
    expect(occurrences(name, "d 0.12")).toBe(1);
  });

  it("announces finite residual evidence once when it is the fallback measurement", () => {
    const name = renderPair({
      ...BASE_PAIR,
      observed_response: null,
      expected_response: null,
      leftover_map_rank: null,
    });

    expect(occurrences(name, "R +0.40")).toBe(1);
    expect(occurrences(name, "d 0.12")).toBe(1);
  });
});
