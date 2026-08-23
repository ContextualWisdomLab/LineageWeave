import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LineageDag } from "./LineageDag";
import type { LineageGraph } from "./api";

const a100Graph: LineageGraph = {
  nodes: [
    {
      id: "rec-002",
      group: "A-100",
      label: "Pricing renegotiation follow-up",
      occurred_at: "2026-01-06T00:00:00",
      is_root: false,
      is_branch_point: true,
    },
    {
      id: "rec-003",
      group: "A-100",
      label: "Pricing renegotiation: revised quote sent",
      occurred_at: "2026-01-10T00:00:00",
      is_root: false,
      is_branch_point: false,
    },
    {
      id: "rec-004",
      group: "A-100",
      label: "Delivery schedule question raised",
      occurred_at: "2026-01-07T00:00:00",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [
    {
      source: "rec-002",
      target: "rec-003",
      fused_score: 0.9,
      interval_relation_code: "interval_contains",
      interval_relation_label: "Contains",
    },
    {
      source: "rec-002",
      target: "rec-004",
      fused_score: 0.85,
      interval_relation_code: "interval_overlaps",
      interval_relation_label: "Overlaps",
    },
  ],
};

describe("LineageDag", () => {
  it("shows Contains and Overlaps as visible text, not hover-only", () => {
    render(<LineageDag graph={a100Graph} onSelectPost={() => undefined} currentPostId="rec-002" />);
    expect(screen.getAllByText("Contains").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Overlaps").length).toBeGreaterThan(0);
    expect(screen.getByRole("list", { name: "Interval relations" })).toBeInTheDocument();
  });

  it("opens the revised quote from the Contains keyboard row", async () => {
    const onSelectPost = vi.fn();
    render(<LineageDag graph={a100Graph} onSelectPost={onSelectPost} currentPostId="rec-002" />);
    await userEvent.click(
      screen.getByRole("button", {
        name: "Contains: open Pricing renegotiation: revised quote sent",
      }),
    );
    expect(onSelectPost).toHaveBeenCalledWith("rec-003");
  });
});
