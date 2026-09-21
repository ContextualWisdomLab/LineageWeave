import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { LeftoverPair } from "../api";
import { LeftoverPairList } from "./LeftoverPairList";

const PAIR: LeftoverPair = {
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
      leftover_map_unexplained: 0.05,
      leftover_map_reconstruction: 0.35,
      leftover_map_cross_share: 0.13,
    },
    "0.13",
  ],
  [
    "unexplained share",
    {
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

function criterionLabel(code: string): string {
  return code === "sales_lead_quality" ? "sales-lead" : code;
}

function occurrences(value: string, token: string): number {
  return value.split(token).length - 1;
}

function accessibleNameFor(overrides: Partial<LeftoverPair> = {}): string {
  render(
    <LeftoverPairList
      pairs={[{ ...PAIR, ...overrides }]}
      criterionLabel={criterionLabel}
      onSelectPost={vi.fn()}
    />,
  );
  return (
    screen
      .getByRole("button", { name: /^Closest leftover: Public post · sales-lead / })
      .getAttribute("aria-label") ?? ""
  );
}

describe("LeftoverPairList accessible action name", () => {
  it("starts with the rendered label and carries each finite evidence value once", async () => {
    const onSelectPost = vi.fn();
    render(
      <LeftoverPairList
        pairs={[PAIR]}
        criterionLabel={criterionLabel}
        onSelectPost={onSelectPost}
      />,
    );

    const action = screen.getByRole("button", {
      name: /^Closest leftover: Public post · sales-lead /,
    });
    expect(action).toHaveTextContent("Closest leftover: Public post · sales-lead");
    expect(action).toHaveAccessibleName(/R \+0\.40/);
    expect(action).toHaveAccessibleName(/Y 2\.40 · E 2\.00/);
    expect(action).toHaveAccessibleName(/rank 1/);
    expect(action).toHaveAccessibleName(/d 0\.12/);

    const name = action.getAttribute("aria-label") ?? "";
    expect(occurrences(name, "rank 1")).toBe(1);
    expect(occurrences(name, "Y 2.40")).toBe(1);
    expect(occurrences(name, "E 2.00")).toBe(1);
    expect(occurrences(name, "R +0.40")).toBe(1);
    expect(occurrences(name, "d 0.12")).toBe(1);

    await userEvent.click(action);
    expect(onSelectPost).toHaveBeenCalledWith(PAIR);
  });

  it("keeps residual guidance while announcing finite residual evidence once", () => {
    const name = accessibleNameFor({
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
      const name = accessibleNameFor(overrides);
      expect(occurrences(name, token)).toBe(1);
    },
  );

  it("keeps every finite persisted pair-evidence badge in the same accessible name", () => {
    render(
      <LeftoverPairList
        pairs={[
          {
            ...PAIR,
            leftover_map_unexplained: 0.05,
            leftover_map_reconstruction: 0.35,
            leftover_map_cross_share: 0.12,
            leftover_map_unexplained_share: 0.02,
            leftover_map_explained_share: 0.76,
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

    const action = screen.getByRole("button", {
      name: /^Closest leftover: Public post · sales-lead /,
    });
    expect(action).toHaveAccessibleName(/R \+0\.40/);
    expect(action).toHaveAccessibleName(/Y 2\.40 · E 2\.00/);
    expect(action).toHaveAccessibleName(/rank 1/);
    expect(action).toHaveAccessibleName(/U \+0\.05/);
    expect(action).toHaveAccessibleName(/U²\/R² 0\.02/);
    expect(action).toHaveAccessibleName(/R̂²\/R² 0\.76/);
    expect(action).toHaveAccessibleName(/2R̂U\/R² 0\.12/);
    expect(action).toHaveAccessibleName(/R̂ \+0\.35/);
    expect(action).toHaveAccessibleName(/ξ \(\+0\.50, \+0\.10\) ζ \(\+0\.50, −0\.02\)/);
    expect(action).toHaveAccessibleName(/d 0\.12/);
  });

  it("keeps non-finite residual visual disclosure while omitting it and non-finite distance from the accessible name", () => {
    render(
      <LeftoverPairList
        pairs={[
          {
            ...PAIR,
            leftover_residual: Number.NaN,
            leftover_distance: Number.NaN,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );

    const action = screen.getByRole("button", {
      name: /^Closest leftover: Public post · sales-lead /,
    });
    expect(action).toHaveAccessibleName(/rank 1/);
    expect(action).not.toHaveAccessibleName(/R —/);
    expect(action).not.toHaveAccessibleName(/d NaN/);
    expect(action).toHaveTextContent("R —");
    expect(action).not.toHaveTextContent("d NaN");
  });

  it("falls back to the existing localized open action while preserving the visual non-finite residual marker", () => {
    render(
      <LeftoverPairList
        pairs={[
          {
            ...PAIR,
            leftover_residual: Number.NaN,
            leftover_distance: Number.NaN,
            observed_response: null,
            expected_response: null,
            leftover_map_rank: null,
          },
        ]}
        criterionLabel={criterionLabel}
        onSelectPost={vi.fn()}
      />,
    );

    const action = screen.getByRole("button", {
      name: /^Closest leftover: Public post · sales-lead /,
    });
    expect(action).toHaveTextContent(
      "Open this post so the leftover criterion is current in Post quality.",
    );
    expect(action).not.toHaveAccessibleName(/R —/);
    expect(action).not.toHaveAccessibleName(/d NaN/);
    expect(action).toHaveTextContent("R —");
    expect(action).not.toHaveTextContent("d NaN");
  });
});
