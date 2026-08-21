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
  it("shows the TEPP contract boundary and opens only supplied source evidence", () => {
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
    expect(screen.getByText(/2 participants/i)).toBeInTheDocument();

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
    expect(screen.queryByText(/participants/i)).not.toBeInTheDocument();
  });
});
