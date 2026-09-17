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

function criterionLabel(code: string): string {
  return code === "sales_lead_quality" ? "sales-lead" : code;
}

describe("LeftoverPairList accessible action name", () => {
  it("starts with the rendered label and carries the finite evidence on the action", async () => {
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

    await userEvent.click(action);
    expect(onSelectPost).toHaveBeenCalledWith(PAIR);
  });

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

  it("omits non-finite residual and distance from both rendering and the accessible name", () => {
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
    expect(action).not.toHaveTextContent("R —");
    expect(action).not.toHaveTextContent("d NaN");
  });
});
