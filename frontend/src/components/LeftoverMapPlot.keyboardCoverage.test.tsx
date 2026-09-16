import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { LeftoverPair } from "../api";
import { LeftoverMapPlot } from "./LeftoverMapPlot";

const PAIR: LeftoverPair = {
  pair_kind: "closest",
  post_id: "post-demo-public",
  post_title: "Public post",
  criterion_code: "sales_lead_quality",
  leftover_distance: 0.12,
  leftover_residual: 0.4,
  leftover_map_person_axis_1: 0.5,
  leftover_map_person_axis_2: 0.1,
  leftover_map_item_axis_1: 0.5,
  leftover_map_item_axis_2: -0.02,
};

describe("LeftoverMapPlot keyboard activation", () => {
  it("ignores non-activation keys on a post marker", () => {
    const onSelectPost = vi.fn();
    render(
      <LeftoverMapPlot
        pairs={[PAIR]}
        criterionLabel={(code) => code}
        onSelectPost={onSelectPost}
      />,
    );

    const postMarker = screen.getByRole("button");
    fireEvent.keyDown(postMarker, { key: "ArrowRight" });

    expect(onSelectPost).not.toHaveBeenCalled();
  });
});
