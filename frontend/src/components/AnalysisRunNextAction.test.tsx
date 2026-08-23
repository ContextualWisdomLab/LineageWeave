import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AnalysisRun } from "../api";
import { AnalysisRunNextAction } from "./AnalysisRunNextAction";

function run(
  partial: Pick<AnalysisRun, "run_kind_code" | "status_code"> & Partial<AnalysisRun>,
): AnalysisRun {
  return {
    analysis_run_id: "run-1",
    run_kind_label: "Lineage reconstruction",
    scope_kind_code: "analysis_scope_corporate_entity",
    scope_kind_label: "Corporate entity",
    scope_entity_name: "Demo Corp",
    status_label: "Running",
    knowledge_cutoff: "2026-01-12T12:00:00Z",
    requested_at: "2026-01-12T12:31:00Z",
    source_counts: [],
    ...partial,
  };
}

describe("AnalysisRunNextAction", () => {
  it("refreshes a running lineage result and does not offer start-over", async () => {
    const onStart = vi.fn();
    const onRefresh = vi.fn();
    render(
      <AnalysisRunNextAction
        run={run({ run_kind_code: "analysis_run_lineage", status_code: "analysis_status_running" })}
        onStart={onStart}
        onRefresh={onRefresh}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Refresh this run. Reconstruction is already queued on the durable outbox.",
    );
    expect(screen.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Refresh this run" }));
    expect(onRefresh).toHaveBeenCalledTimes(1);
    expect(onStart).not.toHaveBeenCalled();
  });

  it("retries failed lineage and does not offer TEPP or start-over", () => {
    render(
      <AnalysisRunNextAction
        run={run({
          run_kind_code: "analysis_run_lineage",
          status_code: "analysis_status_failed",
          status_label: "Failed",
        })}
        onStart={() => undefined}
        onRefresh={() => undefined}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(/retry reconstruction/i);
    expect(screen.getByRole("status")).not.toHaveTextContent(/measurement service|TEPP|calibrated/i);
    expect(screen.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start TEPP measurement" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refresh this run" })).not.toBeInTheDocument();
  });

  it("starts pending TEPP measurement and does not offer reconstruction", () => {
    render(
      <AnalysisRunNextAction
        run={run({
          run_kind_code: "analysis_run_tepp",
          run_kind_label: "TEPP measurement",
          status_code: "analysis_status_pending",
          status_label: "Pending",
        })}
        onStart={() => undefined}
        onRefresh={() => undefined}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("not a calibrated result");
    expect(screen.getByRole("button", { name: "Start TEPP measurement" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refresh this run" })).not.toBeInTheDocument();
  });
});
