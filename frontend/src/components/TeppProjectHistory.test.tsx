import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TeppProjectHistory } from "./TeppProjectHistory";
import type { TeppProjectHistoryProjection } from "../api";

const projection: TeppProjectHistoryProjection = {
  contract_version: 1,
  project_key: "P-100",
  project_name: "Northridge renewal",
  focus_event_id: "voc",
  history_span_start: "2022-03-11T09:00:00Z",
  history_span_end: "2026-08-10T09:00:00Z",
  participant_count: 3,
  inference_status: "temporal_association_only",
  events: [
    {
      event_id: "award",
      event_type_code: "contract_awarded",
      event_title: "수주",
      occurred_at: "2022-03-11T09:00:00Z",
      available_at: "2022-03-11T09:00:00Z",
      availability_basis_code: "source_created_at_proxy",
      source_post_id: "post-award",
      evidence_text: "계약 체결 근거",
      actor_ids: ["a"],
    },
    {
      event_id: "spec",
      event_type_code: "specification_changed",
      event_title: "사양 변경",
      occurred_at: "2023-06-15T09:00:00Z",
      available_at: "2023-06-15T09:00:00Z",
      availability_basis_code: "source_created_at_proxy",
      source_post_id: "post-spec",
      evidence_text: "사양 변경 근거",
      actor_ids: ["a", "b"],
    },
    {
      event_id: "delivery",
      event_type_code: "delivered",
      event_title: "납품",
      occurred_at: "2024-02-20T09:00:00Z",
      available_at: "2024-02-20T09:00:00Z",
      availability_basis_code: "source_created_at_proxy",
      source_post_id: "post-delivery",
      evidence_text: "납품 근거",
      actor_ids: ["b"],
    },
    {
      event_id: "voc",
      event_type_code: "voc_received",
      event_title: "VOC 접수",
      occurred_at: "2026-07-30T09:00:00Z",
      available_at: "2026-07-30T09:00:00Z",
      availability_basis_code: "source_created_at_proxy",
      source_post_id: "post-voc",
      evidence_text: "VOC 근거",
      actor_ids: ["c"],
    },
    {
      event_id: "rebid",
      event_type_code: "rebid_started",
      event_title: "재입찰",
      occurred_at: "2026-08-10T09:00:00Z",
      available_at: "2026-08-10T09:00:00Z",
      availability_basis_code: "source_created_at_proxy",
      source_post_id: "post-rebid",
      evidence_text: "재입찰 근거",
      actor_ids: ["c"],
    },
  ],
  findings: [
    {
      finding_code: "specification_change_and_handoff_before_focus",
      summary: "Explicit specification-change and handoff events precede the focus event.",
      related_event_ids: ["spec", "handoff"],
      evidence_post_ids: ["post-spec", "post-handoff"],
    },
  ],
};

describe("TeppProjectHistory", () => {
  it("renders an accessible project timeline and opens exact source evidence", () => {
    const onOpenPost = vi.fn();
    render(<TeppProjectHistory projection={projection} onOpenPost={onOpenPost} />);

    expect(screen.getByRole("heading", { name: "Project event timeline" })).toBeInTheDocument();
    expect(screen.getByText("Northridge renewal")).toBeInTheDocument();
    expect(screen.getByText("3 explicit participants")).toBeInTheDocument();
    expect(screen.getByText("수주")).toBeInTheDocument();
    expect(screen.getByText("사양 변경")).toBeInTheDocument();
    expect(screen.getByText("납품")).toBeInTheDocument();
    expect(screen.getByText("VOC 접수").closest("li")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("재입찰")).toBeInTheDocument();
    expect(screen.getByText(/temporal association, not causality/i)).toBeInTheDocument();
    expect(screen.getByText(/source-created time is an availability proxy/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open evidence: 사양 변경" }));
    expect(onOpenPost).toHaveBeenCalledWith("post-spec");
  });
});
