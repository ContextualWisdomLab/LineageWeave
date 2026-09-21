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

const ACTION_EVIDENCE_CASES: Array<[string, Partial<LeftoverPair>, string]> = [
  [
    "rank-only",
    { observed_response: null, expected_response: null, leftover_map_rank: 2 },
    "rank 2",
  ],
  ["observed/expected", { leftover_map_rank: null }, "Y 2.40"],
  ["unexplained", { leftover_map_unexplained: 0.05 }, "U +0.05"],
  [
    "reconstruction",
    { leftover_map_unexplained: 0.05, leftover_map_reconstruction: 0.35 },
    "R̂ +0.35",
  ],
  [
    "cross share",
    {
      leftover_distance: 0.99,
      leftover_map_unexplained: 0.05,
      leftover_map_reconstruction: 0.35,
      leftover_map_cross_share: 0.13,
    },
    "0.13",
  ],
  [
    "unexplained share",
    {
      leftover_distance: 0.99,
      leftover_map_unexplained: 0.05,
      leftover_map_reconstruction: 0.35,
      leftover_map_cross_share: 0.13,
      leftover_map_unexplained_share: 0.23,
    },
    "0.23",
  ],
  [
    "explained share",
    {
      leftover_distance: 0.99,
      leftover_map_unexplained: 0.05,
      leftover_map_reconstruction: 0.35,
      leftover_map_cross_share: 0.13,
      leftover_map_unexplained_share: 0.23,
      leftover_map_explained_share: 0.76,
    },
    "0.76",
  ],
  [
    "coordinates",
    {
      leftover_distance: 0.99,
      leftover_map_unexplained: 0.05,
      leftover_map_reconstruction: 0.35,
      leftover_map_cross_share: 0.13,
      leftover_map_unexplained_share: 0.23,
      leftover_map_explained_share: 0.76,
      leftover_map_person_axis_1: 0.5,
      leftover_map_person_axis_2: 0.1,
      leftover_map_item_axis_1: 0.5,
      leftover_map_item_axis_2: -0.02,
    },
    "ξ (+0.50, +0.10)",
  ],
];

function renderPair(pair: LeftoverPair): string {
  render(
    <LeftoverPairList
      pairs={[pair]}
      criterionLabel={() => "sales-lead"}
      onSelectPost={vi.fn()}
    />,
  );
  return (
    screen
      .getByRole("button", { name: /^Closest leftover: Public post · sales-lead/ })
      .getAttribute("aria-label") ?? ""
  );
}

function occurrences(value: string, token: string): number {
  return value.split(token).length - 1;
}

describe("LeftoverPairList accessible evidence", () => {
  it("keeps rank guidance while announcing rank and observed/expected evidence once", () => {
    const name = renderPair(BASE_PAIR);

    expect(name).toContain(
      "Read leftover map rank 1, observed Y 2.40, and expected E 2.00 after IRT main effects, then open this post.",
    );
    expect(occurrences(name, "rank 1")).toBe(1);
    expect(occurrences(name, "Y 2.40")).toBe(1);
    expect(occurrences(name, "E 2.00")).toBe(1);
    expect(occurrences(name, "R +0.40")).toBe(1);
    expect(occurrences(name, "d 0.12")).toBe(1);
  });

  it("keeps residual guidance while announcing finite residual evidence once", () => {
    const name = renderPair({
      ...BASE_PAIR,
      observed_response: null,
      expected_response: null,
      leftover_map_rank: null,
    });

    expect(name).toContain(
      "Leftover residual R +0.40 after IRT main effects. Open this post to read sales-lead.",
    );
    expect(occurrences(name, "R +0.40")).toBe(1);
    expect(occurrences(name, "d 0.12")).toBe(1);
  });

  it.each(ACTION_EVIDENCE_CASES)(
    "announces %s action evidence once",
    (_label, overrides, token) => {
      const name = renderPair({ ...BASE_PAIR, ...overrides });

      expect(occurrences(name, token)).toBe(1);
    },
  );
});
