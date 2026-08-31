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
  event_count: 3,
  distinct_observed_actor_count: 2,
  truncated: false,
  events: [
    {
      event_id: "award",
      source_post_id: "post-award",
      event_title: "Contract awarded",
      event_type_code: "source_recorded",
      event_type_basis_code: "controlled_source_code",
      occurred_at: "2022-03-11T09:00:00Z",
      time_basis_code: "source_post_created_at_fallback",
      voc_type_code: null,
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      observed_responsibilities: [
        {
          actor_key: "person:sales",
          actor_name: "Kim OO",
          actor_type_code: "prov_person",
          affiliated_organization_name: "Demo Corp",
          responsibility: "Observed award owner",
          truth_status_code: "observed",
          provenance: "post_summary_role",
        },
      ],
      responsibility_transition_code: null,
      related_prior_paths: [],
    },
    {
      event_id: "spec",
      source_post_id: "post-spec",
      event_title: "Specification changed",
      event_type_code: "source_recorded",
      event_type_basis_code: "controlled_source_code",
      occurred_at: "2023-06-15T09:00:00Z",
      time_basis_code: "source_post_created_at_fallback",
      voc_type_code: null,
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      observed_responsibilities: [
        {
          actor_key: "person:pm",
          actor_name: "Park OO",
          actor_type_code: "prov_person",
          affiliated_organization_name: "Demo Corp",
          responsibility: "Observed specification owner",
          truth_status_code: "observed",
          provenance: "post_summary_role",
        },
      ],
      responsibility_transition_code: "handoff",
      related_prior_paths: [],
    },
    {
      event_id: "voc",
      source_post_id: "post-voc",
      event_title: "VOC received",
      event_type_code: "voc_received",
      event_type_basis_code: "controlled_source_code",
      occurred_at: "2026-02-02T09:00:00Z",
      time_basis_code: "document_time",
      voc_type_code: "voc",
      source_stage_code: "delivery",
      source_detail_state_code: "delivered",
      project_matches: [],
      observed_responsibilities: [],
      responsibility_transition_code: "assignment_gap",
      related_prior_paths: [
        {
          source_event_id: "award",
          target_event_id: "voc",
          event_ids: ["award", "spec", "voc"],
          edges: [
            {
              parent_event_id: "award",
              child_event_id: "spec",
              fused_score: 0.91,
              temporal_evidence: {
                truth_status_code: "inferred",
                interval_relations: ["before"],
                artifact_digest_sha256: "a".repeat(64),
              },
            },
            { parent_event_id: "spec", child_event_id: "voc", fused_score: 0.73 },
          ],
          minimum_fused_score: 0.73,
          truth_status_code: "inferred",
          source_relation_code: "post_lineage_edge",
          provenance: "post_lineage_edge.fused_score",
        },
        {
          source_event_id: "award",
          target_event_id: "voc",
          event_ids: ["award", "voc"],
          edges: [
            { parent_event_id: "award", child_event_id: "voc", fused_score: 0.68 },
          ],
          minimum_fused_score: 0.68,
          truth_status_code: "inferred",
          source_relation_code: "post_lineage_edge",
          provenance: "post_lineage_edge.fused_score",
        },
      ],
    },
  ],
};

describe("ProjectHistoryTimeline", () => {
  it("shows the focus event, evidence gap, and non-causal prior history", () => {
    const onOpenPost = vi.fn();
    render(<ProjectHistoryTimeline projection={projection} onOpenPost={onOpenPost} />);

    const vocTab = screen.getByRole("tab", { name: /VOC received/ });
    expect(vocTab).toHaveAttribute("aria-selected", "true");
    expect(vocTab).toHaveAttribute("aria-current", "step");
    expect(screen.getAllByText(/evidence gap/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/related history, not causality/i)).toBeInTheDocument();
    expect(screen.getByText("Recorded event time")).toBeInTheDocument();
    expect(screen.queryByText("document_time")).not.toBeInTheDocument();
    expect(screen.getByText("delivery")).toBeInTheDocument();
    expect(screen.getByText("delivered")).toBeInTheDocument();
    expect(screen.getByText(/Time order checked/)).toBeInTheDocument();
    expect(screen.getByText("Contract awarded → Specification changed → VOC received")).toBeVisible();
    expect(screen.getByText("Contract awarded → VOC received")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /open source record: VOC received/i }));
    expect(onOpenPost).toHaveBeenCalledWith("post-voc");
  });

  it("uses roving keyboard selection and a labelled tabpanel", () => {
    render(<ProjectHistoryTimeline projection={projection} onOpenPost={vi.fn()} />);
    const vocTab = screen.getByRole("tab", { name: /VOC received/ });

    fireEvent.keyDown(vocTab, { key: "ArrowLeft" });
    const specTab = screen.getByRole("tab", { name: /Specification changed/ });
    expect(specTab).toHaveFocus();
    expect(specTab).toHaveAttribute("aria-selected", "true");

    const panel = screen.getByRole("tabpanel");
    expect(panel).toHaveAttribute("aria-labelledby", specTab.id);
  });

  it("preserves the selected tab when a parent recreates an equal events array", () => {
    const { rerender } = render(
      <ProjectHistoryTimeline projection={projection} onOpenPost={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("tab", { name: /Specification changed/ }));

    rerender(
      <ProjectHistoryTimeline
        projection={{ ...projection, events: [...projection.events] }}
        onOpenPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("tab", { name: /Specification changed/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});
