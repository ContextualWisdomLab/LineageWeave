import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ProjectHistoryEvent, ProjectHistoryProjection } from "../projectHistory";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";

function historyEvent(eventId: string, title: string): ProjectHistoryEvent {
  return {
    event_id: eventId,
    source_post_id: `post-${eventId}`,
    event_title: title,
    event_type_code: "source_recorded",
    event_type_basis_code: "controlled_source_code",
    occurred_at: "2026-01-02T03:04:05Z",
    time_basis_code: "source_post_created_at_fallback",
    voc_type_code: null,
    source_stage_code: null,
    source_detail_state_code: null,
    project_matches: [],
    observed_responsibilities: [],
    responsibility_transition_code: null,
    related_prior_paths: [],
  };
}

function historyProjection(): ProjectHistoryProjection {
  return {
    contract_version: 1,
    project_key: "P-KEYBOARD",
    normalized_project_key: "p-keyboard",
    project_name: "Keyboard history",
    focus_event_id: "third",
    time_basis_code: "source_post_created_at_fallback",
    event_count: 3,
    distinct_observed_actor_count: 0,
    truncated: false,
    events: [
      historyEvent("first", "First event"),
      historyEvent("second", "Second event"),
      historyEvent("third", "Third event"),
    ],
  };
}

describe("ProjectHistoryTimeline coverage contracts", () => {
  it("implements the complete roving-tab keyboard contract including wraparound", () => {
    render(<ProjectHistoryTimeline projection={historyProjection()} onOpenPost={vi.fn()} />);

    const first = screen.getByRole("tab", { name: /First event/ });
    const second = screen.getByRole("tab", { name: /Second event/ });
    const third = screen.getByRole("tab", { name: /Third event/ });

    fireEvent.keyDown(third, { key: "ArrowRight" });
    expect(first).toHaveFocus();
    expect(first).toHaveAttribute("aria-selected", "true");

    fireEvent.keyDown(first, { key: "ArrowLeft" });
    expect(third).toHaveFocus();

    fireEvent.keyDown(third, { key: "ArrowUp" });
    expect(second).toHaveFocus();

    fireEvent.keyDown(second, { key: "ArrowDown" });
    expect(third).toHaveFocus();

    fireEvent.keyDown(third, { key: "Home" });
    expect(first).toHaveFocus();

    fireEvent.keyDown(first, { key: "End" });
    expect(third).toHaveFocus();

    fireEvent.keyDown(third, { key: "Escape" });
    expect(third).toHaveFocus();
    expect(third).toHaveAttribute("aria-selected", "true");
  });

  it("keeps fallback, truncation, identity-evidence, and unknown-path states buyer-visible", () => {
    const fallbackEvent: ProjectHistoryEvent = {
      ...historyEvent("fallback", "Fallback event"),
      occurred_at: "not-a-date",
      project_matches: [
        {
          match_kind_code: "project_name",
          matched_value: "Recorded project alias",
          truth_status_code: "observed",
          confidence: null,
          ontology_iri: null,
          provenance: "source_record",
        },
      ],
      observed_responsibilities: [
        {
          actor_key: "actor-without-organization",
          actor_name: "Ada Analyst",
          actor_type_code: "person",
          affiliated_organization_name: null,
          responsibility: "Reviews evidence",
          truth_status_code: "observed",
          provenance: "source_record",
        },
      ],
      related_prior_paths: [
        {
          source_event_id: "unknown-prior",
          target_event_id: "fallback",
          event_ids: ["unknown-prior", "fallback"],
          edges: [
            {
              parent_event_id: "unknown-prior",
              child_event_id: "fallback",
              fused_score: 0.625,
            },
          ],
          minimum_fused_score: 0.625,
          truth_status_code: "inferred",
          source_relation_code: "post_lineage_edge",
          provenance: "post_lineage_edge.fused_score",
        },
      ],
    };
    const projection: ProjectHistoryProjection = {
      contract_version: 1,
      project_key: "P-FALLBACK",
      normalized_project_key: "p-fallback",
      project_name: "Fallback history",
      focus_event_id: "missing-focus",
      time_basis_code: "source_post_created_at_fallback",
      event_count: 1,
      distinct_observed_actor_count: 1,
      truncated: true,
      events: [fallbackEvent],
    };

    render(<ProjectHistoryTimeline projection={projection} onOpenPost={vi.fn()} />);

    expect(screen.getByRole("status")).toHaveTextContent(/timeline is truncated/i);
    expect(screen.getByRole("tab", { name: /Fallback event/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getAllByText("not-a-date").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ada Analyst").length).toBe(2);
    expect(screen.getByText("Reviews evidence")).toBeInTheDocument();
    expect(screen.getByText("Recorded project alias")).toBeInTheDocument();
    expect(screen.getByText(/unknown-prior → Fallback event/)).toBeInTheDocument();
    expect(screen.getAllByText("0.625").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Not applicable").length).toBeGreaterThan(0);
    expect(screen.getByText("Source creation time")).toBeInTheDocument();
  });

  it("renders an empty exact-value table without inventing an event selection", () => {
    const empty: ProjectHistoryProjection = {
      contract_version: 1,
      project_key: "P-EMPTY",
      normalized_project_key: "p-empty",
      project_name: "Empty history",
      focus_event_id: "missing",
      time_basis_code: "source_post_created_at_fallback",
      event_count: 0,
      distinct_observed_actor_count: 0,
      truncated: false,
      events: [],
    };

    render(<ProjectHistoryTimeline projection={empty} onOpenPost={vi.fn()} />);

    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
    expect(screen.queryByRole("tabpanel")).not.toBeInTheDocument();
    expect(screen.getByRole("table", { name: /project history exact values/i })).toBeInTheDocument();
  });
});
