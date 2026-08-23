import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ProjectHistoryProjection } from "../projectHistory";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";

const projection: ProjectHistoryProjection = {
  contract_version: 1,
  project_key: "P-100",
  normalized_project_key: "p-100",
  project_name: "Transformer renewal",
  focus_event_id: "voc",
  time_basis_code: "source_post_created_at_fallback",
  knowledge_cutoff: "2026-08-20T00:00:00+00:00",
  evidence_boundary_code: "authorized_visible_source_posts",
  event_count: 3,
  connected_post_count: 3,
  lineage_count: 1,
  distinct_actor_count: 2,
  distinct_observed_actor_count: 1,
  truncated: false,
  events: [
    {
      event_id: "award",
      source_post_id: "post-award",
      event_title: "Contract awarded",
      event_type_code: "contract_awarded",
      event_type_basis_code: "display_classification",
      occurred_at: "2022-03-11T09:00:00Z",
      time_basis_code: "source_post_created_at_fallback",
      voc_type_code: null,
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      responsibility_evidence: [
        {
          actor_key: "text:prov_person\u001fkim oo\u001fdemo corp",
          actor_name: "Kim OO",
          actor_type_code: "prov_person",
          affiliated_organization_name: "Demo Corp",
          responsibility: "Source author",
          truth_status_code: "observed",
          provenance: "source_post.source_author",
        },
      ],
      observed_responsibilities: [
        {
          actor_key: "text:prov_person\u001fkim oo\u001fdemo corp",
          actor_name: "Kim OO",
          actor_type_code: "prov_person",
          affiliated_organization_name: "Demo Corp",
          responsibility: "Source author",
          truth_status_code: "observed",
          provenance: "source_post.source_author",
        },
      ],
      responsibility_transition_code: null,
      responsibility_transition_truth_status_code: null,
      related_prior_paths: [],
    },
    {
      event_id: "spec",
      source_post_id: "post-spec",
      event_title: "Specification changed",
      event_type_code: "specification_changed",
      event_type_basis_code: "display_classification",
      occurred_at: "2023-06-15T09:00:00Z",
      time_basis_code: "source_post_created_at_fallback",
      voc_type_code: null,
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      responsibility_evidence: [
        {
          actor_key: "person:pm",
          actor_name: "Park OO",
          actor_type_code: "prov_person",
          affiliated_organization_name: "Demo Corp",
          responsibility: "Coordinate the specification revision",
          truth_status_code: "inferred",
          provenance: "post_summary_role",
        },
      ],
      observed_responsibilities: [],
      responsibility_transition_code: "handoff",
      responsibility_transition_truth_status_code: "inferred",
      related_prior_paths: [],
    },
    {
      event_id: "voc",
      source_post_id: "post-voc",
      event_title: "VOC received",
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
      responsibility_transition_code: "assignment_gap",
      responsibility_transition_truth_status_code: "inferred",
      related_prior_paths: [
        {
          source_event_id: "award",
          target_event_id: "voc",
          event_ids: ["award", "spec", "voc"],
          edges: [
            { parent_event_id: "award", child_event_id: "spec", fused_score: 0.91 },
            { parent_event_id: "spec", child_event_id: "voc", fused_score: 0.73 },
          ],
          minimum_fused_score: 0.73,
          truth_status_code: "inferred",
          source_relation_code: "post_lineage_edge",
          provenance: "post_lineage_edge.fused_score",
        },
      ],
    },
  ],
};

describe("ProjectHistoryTimeline", () => {
  it("describes a recorded document clock without calling it a source-post fallback", () => {
    render(
      <ProjectHistoryTimeline
        projection={{ ...projection, time_basis_code: "document_time" }}
        onOpenPost={vi.fn()}
      />,
    );

    expect(screen.getByText(/dates use the document time recorded by the source/i)).toBeInTheDocument();
    expect(screen.queryByText(/separate event clock is not recorded/i)).not.toBeInTheDocument();
  });

  it("shows the focus event, evidence gap, authorization boundary, and non-causal prior history", () => {
    const onOpenPost = vi.fn();
    render(<ProjectHistoryTimeline projection={projection} onOpenPost={onOpenPost} />);

    const vocTab = screen.getByRole("tab", { name: /VOC received/ });
    expect(vocTab).toHaveAttribute("aria-selected", "true");
    expect(vocTab).toHaveAttribute("aria-current", "step");
    expect(screen.getByText(/evidence gap/i, { selector: "dd" })).toBeInTheDocument();
    expect(screen.getByText(/related history, not causality/i)).toBeInTheDocument();
    expect(screen.getByText(/permission, visibility, publication, and cutoff gates/i)).toBeInTheDocument();
    expect(screen.getByText(/3 project posts · 3 connected · lineage count 1/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /open source record: VOC received/i }));
    expect(onOpenPost).toHaveBeenCalledWith("post-voc");
  });

  it("uses roving keyboard selection and exposes inferred responsibility truth", () => {
    render(<ProjectHistoryTimeline projection={projection} onOpenPost={vi.fn()} />);
    const vocTab = screen.getByRole("tab", { name: /VOC received/ });

    fireEvent.keyDown(vocTab, { key: "ArrowLeft" });
    const specTab = screen.getByRole("tab", { name: /Specification changed/ });
    expect(specTab).toHaveFocus();
    expect(specTab).toHaveAttribute("aria-selected", "true");

    const panel = screen.getByRole("tabpanel");
    expect(panel).toHaveAttribute("aria-labelledby", specTab.id);
    expect(screen.getAllByText("Inferred").length).toBeGreaterThan(0);
    expect(screen.getByText("post_summary_role")).toBeInTheDocument();
    expect(screen.queryByText("Observed award owner")).not.toBeInTheDocument();
  });

  it("labels the projection's actual time basis", () => {
    const { rerender } = render(
      <ProjectHistoryTimeline projection={projection} onOpenPost={vi.fn()} />,
    );
    expect(
      screen.getByText("Dates use source-post creation time because a separate event clock is not recorded."),
    ).toBeInTheDocument();

    rerender(
      <ProjectHistoryTimeline
        projection={{ ...projection, time_basis_code: "document_time" }}
        onOpenPost={vi.fn()}
      />,
    );
    expect(screen.getByText("Dates use the document time recorded by the source.")).toBeInTheDocument();
  });
});
