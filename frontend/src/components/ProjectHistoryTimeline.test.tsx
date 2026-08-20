import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";
import type { TeppProjectHistory } from "../api";

const history: TeppProjectHistory = {
  contract_version: 1,
  project_key: "project-alpha",
  project_name: "Project Alpha",
  focus_event_id: "event-voc",
  inference_status: "temporal_association_only",
  participant_count: 3,
  history_span_start: "2022-03-01T00:00:00Z",
  history_span_end: "2026-08-01T00:00:00Z",
  events: [
    {
      event_id: "event-contract",
      event_type_code: "contract_awarded",
      event_title: "Contract awarded",
      event_time: "2022-03-01T00:00:00Z",
      available_at: "2022-03-01T00:00:00Z",
      availability_basis: "source_post.created_at",
      source_post_id: "post-contract",
      evidence_text: "The order was awarded.",
      actor_ids: ["actor-sales"],
    },
    {
      event_id: "event-spec",
      event_type_code: "specification_changed",
      event_title: "Specification changed",
      event_time: "2023-06-01T00:00:00Z",
      available_at: "2023-06-01T00:00:00Z",
      availability_basis: "source_post.created_at",
      source_post_id: "post-spec",
      evidence_text: "The specification changed.",
      actor_ids: ["actor-engineering"],
    },
    {
      event_id: "event-voc",
      event_type_code: "voc_received",
      event_title: "VOC received",
      event_time: "2026-06-01T00:00:00Z",
      available_at: "2026-06-01T00:00:00Z",
      availability_basis: "source_post.created_at",
      source_post_id: "post-voc",
      evidence_text: "A customer VOC was registered.",
      actor_ids: ["actor-sales", "actor-operations", "actor-customer"],
    },
  ],
  findings: [
    {
      finding_code: "specification_change_before_focus",
      summary:
        "An explicit specification-change event precedes the focus event. This is a temporal association, not a causal conclusion.",
      related_event_ids: ["event-spec", "event-voc"],
      evidence_post_ids: ["post-spec", "post-voc"],
    },
  ],
};

describe("ProjectHistoryTimeline", () => {
  it("renders the TEPP history, focus event, participants, and evidence navigation", async () => {
    const onOpenPost = vi.fn();
    render(<ProjectHistoryTimeline history={history} onOpenPost={onOpenPost} />);

    expect(screen.getByRole("region", { name: "TEPP project history" })).toBeInTheDocument();
    expect(screen.getByText("Project Alpha")).toBeInTheDocument();
    expect(screen.getByText("Contract awarded")).toBeInTheDocument();
    expect(screen.getByText("Specification changed")).toBeInTheDocument();
    expect(screen.getByText("VOC received")).toBeInTheDocument();
    expect(screen.getByText(/3/)).toBeInTheDocument();
    expect(screen.getByText(/temporal association/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open evidence: VOC received" })).toHaveAttribute(
      "aria-current",
      "step",
    );

    await userEvent.click(screen.getByRole("button", { name: "Open evidence: VOC received" }));
    expect(onOpenPost).toHaveBeenCalledWith("post-voc");
  });
});
