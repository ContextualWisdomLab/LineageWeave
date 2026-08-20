import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ProjectHistoryProjection } from "../projectHistory";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";


const projection: ProjectHistoryProjection = {
  contract_version: 1,
  project_key: "P-100",
  normalized_project_key: "p-100",
  project_name: "Northridge renewal",
  focus_event_id: "voc",
  time_basis_code: "document_time",
  event_count: 5,
  distinct_observed_actor_count: 3,
  truncated: false,
  events: [
    {
      event_id: "award",
      source_post_id: "post-award",
      event_title: "Contract awarded",
      event_type_code: "contract_awarded",
      event_type_basis_code: "display_classification",
      occurred_at: "2022-03-11T09:00:00Z",
      time_basis_code: "document_time",
      voc_type_code: "vom",
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [
        {
          match_kind_code: "source_project_code",
          matched_value: "P-100",
          truth_status_code: "observed",
          confidence: null,
          ontology_iri: null,
          provenance: "source_post.source_project_code",
        },
      ],
      observed_responsibilities: [
        {
          actor_key: "person:ada",
          actor_name: "Ada West",
          actor_type_code: "prov_person",
          affiliated_organization_name: "Demo Corp",
          responsibility: "Own the award",
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
      event_title: "Specification revision requested",
      event_type_code: "specification_changed",
      event_type_basis_code: "display_classification",
      occurred_at: "2023-06-15T09:00:00Z",
      time_basis_code: "document_time",
      voc_type_code: "vom",
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      observed_responsibilities: [
        {
          actor_key: "person:ada",
          actor_name: "Ada West",
          actor_type_code: "prov_person",
          affiliated_organization_name: "Demo Corp",
          responsibility: "Own the specification",
          truth_status_code: "observed",
          provenance: "post_summary_role",
        },
      ],
      responsibility_transition_code: "continuous",
      related_prior_paths: [
        {
          source_event_id: "award",
          target_event_id: "spec",
          event_ids: ["award", "spec"],
          edges: [
            {
              parent_event_id: "award",
              child_event_id: "spec",
              fused_score: 0.91,
            },
          ],
          minimum_fused_score: 0.91,
          truth_status_code: "inferred",
          source_relation_code: "post_lineage_edge",
          provenance: "post_lineage_edge.fused_score",
        },
      ],
    },
    {
      event_id: "delivery",
      source_post_id: "post-delivery",
      event_title: "Delivery confirmed",
      event_type_code: "delivered",
      event_type_basis_code: "display_classification",
      occurred_at: "2024-02-20T09:00:00Z",
      time_basis_code: "document_time",
      voc_type_code: "vom",
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      observed_responsibilities: [
        {
          actor_key: "person:priya",
          actor_name: "Priya Nair",
          actor_type_code: "prov_person",
          affiliated_organization_name: "Northridge Grid",
          responsibility: "Own delivery acceptance",
          truth_status_code: "observed",
          provenance: "post_summary_role",
        },
      ],
      responsibility_transition_code: "handoff",
      related_prior_paths: [
        {
          source_event_id: "award",
          target_event_id: "delivery",
          event_ids: ["award", "spec", "delivery"],
          edges: [
            {
              parent_event_id: "award",
              child_event_id: "spec",
              fused_score: 0.91,
            },
            {
              parent_event_id: "spec",
              child_event_id: "delivery",
              fused_score: 0.82,
            },
          ],
          minimum_fused_score: 0.82,
          truth_status_code: "inferred",
          source_relation_code: "post_lineage_edge",
          provenance: "post_lineage_edge.fused_score",
        },
      ],
    },
    {
      event_id: "voc",
      source_post_id: "post-voc",
      event_title: "VOC received",
      event_type_code: "voc_received",
      event_type_basis_code: "display_classification",
      occurred_at: "2026-07-30T09:00:00Z",
      time_basis_code: "document_time",
      voc_type_code: "voc",
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      observed_responsibilities: [],
      responsibility_transition_code: "assignment_gap",
      related_prior_paths: [
        {
          source_event_id: "award",
          target_event_id: "voc",
          event_ids: ["award", "spec", "delivery", "voc"],
          edges: [
            {
              parent_event_id: "award",
              child_event_id: "spec",
              fused_score: 0.91,
            },
            {
              parent_event_id: "spec",
              child_event_id: "delivery",
              fused_score: 0.82,
            },
            {
              parent_event_id: "delivery",
              child_event_id: "voc",
              fused_score: 0.73,
            },
          ],
          minimum_fused_score: 0.73,
          truth_status_code: "inferred",
          source_relation_code: "post_lineage_edge",
          provenance: "post_lineage_edge.fused_score",
        },
      ],
    },
    {
      event_id: "rebid",
      source_post_id: "post-rebid",
      event_title: "Rebid started",
      event_type_code: "rebid_started",
      event_type_basis_code: "display_classification",
      occurred_at: "2026-08-10T09:00:00Z",
      time_basis_code: "document_time",
      voc_type_code: "vom",
      source_stage_code: null,
      source_detail_state_code: null,
      project_matches: [],
      observed_responsibilities: [
        {
          actor_key: "team:bid",
          actor_name: "Bid team",
          actor_type_code: "prov_team",
          affiliated_organization_name: "Demo Corp",
          responsibility: "Prepare the rebid",
          truth_status_code: "observed",
          provenance: "post_summary_role",
        },
      ],
      responsibility_transition_code: "assignment_gap",
      related_prior_paths: [],
    },
  ],
};


describe("ProjectHistoryTimeline", () => {
  it("renders the focus event, exact evidence, and non-causal prior path", () => {
    const onOpenPost = vi.fn();
    render(<ProjectHistoryTimeline projection={projection} onOpenPost={onOpenPost} />);

    expect(screen.getByRole("heading", { name: "Project event timeline" })).toBeInTheDocument();
    expect(screen.getByText("5 events · 3 observed actors")).toBeInTheDocument();
    const vocTab = screen.getByRole("tab", { name: /VOC received/ });
    expect(vocTab).toHaveAttribute("aria-selected", "true");
    expect(vocTab).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("Assignment evidence gap")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Contract awarded → Specification revision requested → Delivery confirmed → VOC received",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/inferred related history, not causality/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open source record: VOC received" }));
    expect(onOpenPost).toHaveBeenCalledWith("post-voc");
  });

  it("supports roving keyboard selection with visible text for handoffs and gaps", () => {
    render(<ProjectHistoryTimeline projection={projection} onOpenPost={vi.fn()} />);
    const vocTab = screen.getByRole("tab", { name: /VOC received/ });

    fireEvent.keyDown(vocTab, { key: "ArrowLeft" });
    const deliveryTab = screen.getByRole("tab", { name: /Delivery confirmed/ });
    expect(deliveryTab).toHaveAttribute("aria-selected", "true");
    expect(deliveryTab).toHaveFocus();
    expect(screen.getByText("Responsibility handoff")).toBeInTheDocument();
    expect(screen.getByText("Priya Nair")).toBeInTheDocument();

    fireEvent.keyDown(deliveryTab, { key: "Home" });
    expect(screen.getByRole("tab", { name: /Contract awarded/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    fireEvent.keyDown(screen.getByRole("tab", { name: /Contract awarded/ }), { key: "End" });
    expect(screen.getByRole("tab", { name: /Rebid started/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("provides a complete exact-value table for touch, print, and assistive technology", () => {
    render(<ProjectHistoryTimeline projection={projection} onOpenPost={vi.fn()} />);
    fireEvent.click(screen.getByText("Exact values"));

    const table = screen.getByRole("table", { name: "Project history exact values" });
    expect(within(table).getAllByRole("row")).toHaveLength(6);
    expect(within(table).getByText("0.730")).toBeInTheDocument();
    expect(within(table).getByText("Assignment evidence gap")).toBeInTheDocument();
  });
});
