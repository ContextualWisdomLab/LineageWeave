import { describe, expect, it } from "vitest";
import type { AnalysisRun } from "./api";
import {
  analysisRunCanRefresh,
  analysisRunCanStart,
  analysisRunNextAction,
  analysisRunReportPeriod,
  analysisRunStartLabel,
} from "./analysisRunGuidance";

function run(
  partial: Pick<AnalysisRun, "run_kind_code" | "status_code"> & Partial<AnalysisRun>,
): AnalysisRun {
  return {
    analysis_run_id: "run-1",
    run_kind_label:
      partial.run_kind_code === "analysis_run_tepp"
        ? "TEPP measurement"
        : partial.run_kind_code === "analysis_run_report"
          ? "Period report"
          : "Lineage reconstruction",
    scope_kind_code: "analysis_scope_corporate_entity",
    scope_kind_label: "Corporate entity",
    scope_entity_name: "Demo Corp",
    scope_key: "2026-W02",
    status_label: "Status",
    knowledge_cutoff: "2026-01-12T12:00:00Z",
    requested_at: "2026-01-12T12:31:00Z",
    source_counts: [],
    ...partial,
  };
}

describe("analysisRunGuidance", () => {
  it("gives failed lineage a reconstruction next action and no start-over or TEPP copy", () => {
    const failed = run({
      run_kind_code: "analysis_run_lineage",
      status_code: "analysis_status_failed",
    });
    const copy = analysisRunNextAction(failed) ?? "";
    expect(copy.toLowerCase()).toMatch(/reconstruction/);
    expect(copy.toLowerCase()).not.toMatch(/measurement service|tepp/);
    expect(analysisRunCanStart(failed)).toBe(false);
    expect(analysisRunCanRefresh(failed)).toBe(false);
  });

  it("gives failed TEPP a connect-transport next action and no reconstruction control", () => {
    const failed = run({
      run_kind_code: "analysis_run_tepp",
      status_code: "analysis_status_failed",
    });
    const copy = analysisRunNextAction(failed) ?? "";
    expect(copy.toLowerCase()).toMatch(/measurement service/);
    expect(copy.toLowerCase()).not.toMatch(/reconstruction/);
    expect(analysisRunCanStart(failed)).toBe(false);
    expect(analysisRunStartLabel(failed)).toBe("Start TEPP measurement");
  });

  it("gives failed report a rebuild next action and a period to open, not TEPP", () => {
    const failed = run({
      run_kind_code: "analysis_run_report",
      status_code: "analysis_status_failed",
    });
    const copy = analysisRunNextAction(failed) ?? "";
    expect(copy.toLowerCase()).toMatch(/rebuild/);
    expect(copy.toLowerCase()).not.toMatch(/measurement service|reconstruction/);
    expect(analysisRunCanStart(failed)).toBe(false);
    expect(analysisRunReportPeriod(failed)).toBe("2026-W02");
  });

  it("denies a calibrated result on pending TEPP and keeps the TEPP start control", () => {
    const pending = run({
      run_kind_code: "analysis_run_tepp",
      status_code: "analysis_status_pending",
    });
    const copy = analysisRunNextAction(pending) ?? "";
    expect(copy.toLowerCase()).toMatch(/not a calibrated result/);
    expect(copy.toLowerCase()).not.toMatch(/reconstruction has not started/);
    expect(analysisRunCanStart(pending)).toBe(true);
    expect(analysisRunStartLabel(pending)).toBe("Start TEPP measurement");
    expect(analysisRunCanRefresh(pending)).toBe(false);
  });

  it("does not expose start-over when running copy says the work is already queued", () => {
    const runningLineage = run({
      run_kind_code: "analysis_run_lineage",
      status_code: "analysis_status_running",
    });
    const runningTepp = run({
      run_kind_code: "analysis_run_tepp",
      status_code: "analysis_status_running",
    });
    expect(analysisRunNextAction(runningLineage)).toMatch(/already queued/i);
    expect(analysisRunNextAction(runningLineage)?.toLowerCase()).not.toMatch(/measurement service/);
    expect(analysisRunNextAction(runningTepp)?.toLowerCase()).not.toMatch(/reconstruction/);
    expect(analysisRunCanStart(runningLineage)).toBe(false);
    expect(analysisRunCanStart(runningTepp)).toBe(false);
    expect(analysisRunCanRefresh(runningLineage)).toBe(true);
    expect(analysisRunCanRefresh(runningTepp)).toBe(true);
  });

  it("keeps succeeded report copy free of unbuilt/rebuild/reconstruct/measure language", () => {
    const succeeded = run({
      run_kind_code: "analysis_run_report",
      status_code: "analysis_status_succeeded",
    });
    expect(analysisRunNextAction(succeeded)).toBeNull();
    expect(analysisRunCanStart(succeeded)).toBe(false);
    expect(analysisRunReportPeriod(succeeded)).toBe("2026-W02");
  });
});
