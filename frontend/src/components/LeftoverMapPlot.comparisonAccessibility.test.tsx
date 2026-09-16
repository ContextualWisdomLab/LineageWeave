import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { LeftoverPair } from "../api";
import { setLocale } from "../i18n";
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

describe("LeftoverMapPlot comparison post accessibility", () => {
  afterEach(() => setLocale("en"));

  it("composes the comparison marker name from existing localized copy", () => {
    setLocale("ko");
    render(
      <LeftoverMapPlot
        pairs={[PAIR]}
        criterionLabel={() => "sales-lead"}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );

    expect(
      screen.getByRole("button", {
        name: "잔여 지도 비교 그림: 잔여 지도 글 Public post 열기 (ξ (+0.50, +0.10))",
      }),
    ).toBeInTheDocument();
  });

  it("does not invent a post marker when persisted person coordinates are unavailable", () => {
    const { container } = render(
      <LeftoverMapPlot
        pairs={[
          {
            ...PAIR,
            leftover_map_person_axis_1: null,
          },
        ]}
        criterionLabel={() => "sales-lead"}
        onSelectPost={vi.fn()}
        variant="comparison"
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});
