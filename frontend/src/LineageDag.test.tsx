import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LineageDag } from "./LineageDag";

const graph = {
  nodes: [
    {
      id: "rec-001",
      group: "A-100",
      label: "Initial site visit and project scope discussion",
      occurred_at: "2026-01-01T00:00:00",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "rec-002",
      group: "A-100",
      label: "Pricing renegotiation follow-up",
      occurred_at: "2026-01-06T00:00:00",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [{ source: "rec-001", target: "rec-002", fused_score: 0.8 }],
};

describe("LineageDag", () => {
  it("gives every node mark a 24x24px-minimum transparent hit target ahead of the visible mark", () => {
    render(<LineageDag graph={graph} onSelectPost={() => undefined} />);
    const button = screen.getByRole("button", { name: "Open post: Initial site visit and project scope discussion" });
    const circles = button.querySelectorAll("circle");
    expect(circles).toHaveLength(2);

    // The hit circle must come first so the visible mark still paints on top of it.
    const [hit, visible] = circles;
    expect(hit.getAttribute("fill")).toBe("transparent");
    expect(hit.style.pointerEvents).toBe("all");
    // r=12 -> 24px diameter, matching --size-control-min (tokens.css) at the
    // DAG's ~1 SVG-user-unit-per-px scale -- the WCAG 2.5.8 AA minimum.
    expect(Number(hit.getAttribute("r"))).toBeGreaterThanOrEqual(12);
    expect(Number(visible.getAttribute("r"))).toBeLessThan(Number(hit.getAttribute("r")));
  });

  it("still opens the post when the enlarged hit target is clicked", async () => {
    const onSelectPost = vi.fn();
    render(<LineageDag graph={graph} onSelectPost={onSelectPost} />);
    await userEvent.click(screen.getByRole("button", { name: "Open post: Pricing renegotiation follow-up" }));
    expect(onSelectPost).toHaveBeenCalledWith("rec-002");
  });
});
