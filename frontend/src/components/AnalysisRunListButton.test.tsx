import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AnalysisRun } from "../api";
import { AnalysisRunListButton } from "./AnalysisRunListButton";

function pendingTepp(): AnalysisRun {
  return {
    analysis_run_id: "run-demo-tepp",
    run_kind_code: "analysis_run_tepp",
    run_kind_label: "TEPP measurement",
    scope_kind_code: "analysis_scope_corporate_entity",
    scope_kind_label: "Corporate entity",
    scope_entity_name: "Demo Corp",
    status_code: "analysis_status_pending",
    status_label: "Pending",
    knowledge_cutoff: "2026-01-12T12:00:00Z",
    requested_at: "2026-01-12T12:34:00Z",
    source_counts: [
      {
        count_type_code: "analysis_count_document",
        count_type_label: "Documents",
        count_value: 3,
      },
    ],
  };
}

describe("AnalysisRunListButton", () => {
  it("opens the run and names the pending TEPP next action", async () => {
    const onOpen = vi.fn();
    render(<AnalysisRunListButton run={pendingTepp()} onOpen={onOpen} />);
    const button = screen.getByRole("button", {
      name: "Open analysis run: TEPP measurement · Pending · Demo Corp. Open this run to confirm which posts TEPP will measure. Measurement has not started yet — this is not a calibrated result.",
    });
    expect(button).toHaveTextContent("3 documents");
    expect(button).not.toHaveTextContent("Reconstruction");
    await userEvent.click(button);
    expect(onOpen).toHaveBeenCalledWith("run-demo-tepp");
  });
});
