import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { TeppProjectHistoryValidation } from "../projectHistory";
import { TeppProjectHistoryEvidence } from "./TeppProjectHistoryEvidence";

const validation: TeppProjectHistoryValidation = {
  status: "validated",
  next_action_code: "open_source_evidence",
  project_history: {
    contract_version: 1,
    project_key: "P-100",
    project_name: "Synthetic transformer renewal",
    focus_event_id: "voc",
    knowledge_cutoff: "2026-08-20T12:00:00Z",
    history_span_start: "2022-03-11T09:00:00Z",
    history_span_end: "2026-02-02T09:00:00Z",
    participant_count: 2,
    inference_status: "temporal_association_only",
    event_count: 3,
    findings: [
      {
        finding_code: "specification_change_before_focus",
        summary: "An explicit specification-change event precedes the focus event.",
        related_event_ids: ["spec"],
        evidence_post_ids: ["post-spec"],
      },
    ],
  },
};

describe("TeppProjectHistoryEvidence", () => {
  it("shows controlled TEPP copy and opens only supplied source evidence", () => {
    const onOpenPost = vi.fn();
    render(
      <TeppProjectHistoryEvidence
        validation={validation}
        onOpenPost={onOpenPost}
        sourceLabels={{ "post-spec": "Synthetic specification changed" }}
      />,
    );

    expect(screen.getByRole("heading", { name: /TEPP temporal validation/i })).toBeInTheDocument();
    expect(screen.getByText(/temporal association only/i)).toBeInTheDocument();
    expect(screen.getByText(/does not identify a cause/i)).toBeInTheDocument();
    expect(screen.getByText(/participants in supplied evidence/i)).toBeInTheDocument();
    expect(screen.getByText("2", { selector: "dd" })).toBeInTheDocument();
    expect(
      screen.queryByText("An explicit specification-change event precedes the focus event."),
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /open evidence: Synthetic specification changed/i }),
    );
    expect(onOpenPost).toHaveBeenCalledWith("post-spec");
  });

  it("gives an actionable fail-closed state without inventing a result", () => {
    render(
      <TeppProjectHistoryEvidence
        validation={{
          status: "not_configured",
          project_history: null,
          next_action_code: "configure_tepp_project_history",
        }}
        onOpenPost={vi.fn()}
        sourceLabels={{}}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(/configure the TEPP project-history endpoint/i);
    expect(screen.queryByText(/participants in supplied evidence/i)).not.toBeInTheDocument();
  });

  it("uses unique labelled-region ids when more than one evidence panel is present", () => {
    render(
      <>
        <TeppProjectHistoryEvidence
          validation={validation}
          onOpenPost={vi.fn()}
          sourceLabels={{ "post-spec": "Synthetic specification changed" }}
        />
        <TeppProjectHistoryEvidence
          validation={validation}
          onOpenPost={vi.fn()}
          sourceLabels={{ "post-spec": "Synthetic specification changed" }}
        />
      </>,
    );

    const headings = screen.getAllByRole("heading", { name: /TEPP temporal validation/i });
    const regions = headings.map((heading) => heading.closest("section"));
    expect(headings[0].id).not.toBe(headings[1].id);
    expect(regions[0]).toHaveAttribute("aria-labelledby", headings[0].id);
    expect(regions[1]).toHaveAttribute("aria-labelledby", headings[1].id);
  });

  it("fails closed when a validated response has no metadata", () => {
    render(
      <TeppProjectHistoryEvidence
        validation={{
          status: "validated",
          project_history: null,
          next_action_code: "open_source_evidence",
        }}
        onOpenPost={vi.fn()}
        sourceLabels={{}}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent(/open the source evidence/i);
  });
});
