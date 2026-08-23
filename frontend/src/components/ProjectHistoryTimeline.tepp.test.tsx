import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ProjectHistoryProjection } from "../projectHistory";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";

const projection = {
  contract_version: 1,
  project_key: "P-100",
  normalized_project_key: "p-100",
  project_name: "Synthetic transformer renewal",
  focus_event_id: "voc",
  time_basis_code: "source_post_created_at_fallback",
  knowledge_cutoff: "2026-08-20T12:00:00Z",
  evidence_boundary_code: "authorized_visible_source_posts",
  event_count: 1,
  distinct_actor_count: 0,
  distinct_observed_actor_count: 0,
  truncated: false,
  tepp_validation: {
    status: "validated",
    next_action_code: "open_source_evidence",
    project_history: {
      contract_version: 1,
      project_key: "P-100",
      project_name: "Synthetic transformer renewal",
      focus_event_id: "voc",
      knowledge_cutoff: "2026-08-20T12:00:00Z",
      history_span_start: "2026-02-02T09:00:00Z",
      history_span_end: "2026-02-02T09:00:00Z",
      participant_count: 0,
      inference_status: "temporal_association_only",
      event_count: 1,
      findings: [],
    },
  },
  events: [
    {
      event_id: "voc",
      source_post_id: "post-voc",
      event_title: "Synthetic VOC received",
      event_type_code: "voc_received",
      event_type_basis_code: "display_classification",
      occurred_at: "2026-02-02T09:00:00Z",
      time_basis_code: "source_post_created_at_fallback",
      voc_type_code: "voc",
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      responsibility_evidence: [],
      observed_responsibilities: [],
      responsibility_transition_code: null,
      responsibility_transition_truth_status_code: null,
      related_prior_paths: [],
    },
  ],
} as ProjectHistoryProjection;

describe("ProjectHistoryTimeline TEPP integration", () => {
  it("renders TEPP validation on the canonical timeline instead of a duplicate timeline", () => {
    render(<ProjectHistoryTimeline projection={projection} onOpenPost={vi.fn()} />);

    expect(screen.getByRole("heading", { name: /TEPP temporal validation/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Project event timeline/i })).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(1);
  });
});
