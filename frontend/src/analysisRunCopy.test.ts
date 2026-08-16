import { describe, expect, it } from "vitest";
import type { AnalysisRun, AnalysisRunKindCode, AnalysisRunStatusCode } from "./api";
import {
  analysisRunAccessibleName,
  analysisRunCaption,
  analysisRunCorpusHint,
  analysisRunNextAction,
} from "./analysisRunCopy";

function demoRun(overrides: Partial<AnalysisRun> = {}): AnalysisRun {
  return {
    analysis_run_id: "run-demo",
    run_kind_code: "analysis_run_lineage",
    run_kind_label: "Lineage reconstruction",
    scope_kind_code: "analysis_scope_corporate_entity",
    scope_kind_label: "Corporate entity",
    scope_entity_name: "Demo Corp",
    status_code: "analysis_status_pending",
    status_label: "Pending",
    knowledge_cutoff: "2026-01-12T12:00:00Z",
    requested_at: "2026-01-12T12:30:00Z",
    source_counts: [],
    ...overrides,
  };
}

const KIND_LABEL: Record<AnalysisRunKindCode, string> = {
  analysis_run_lineage: "Lineage reconstruction",
  analysis_run_tepp: "TEPP measurement",
  analysis_run_report: "Period report",
};

const STATUS_LABEL: Record<AnalysisRunStatusCode, string> = {
  analysis_status_pending: "Pending",
  analysis_status_running: "Running",
  analysis_status_succeeded: "Succeeded",
  analysis_status_failed: "Failed",
  analysis_status_cancelled: "Cancelled",
};

describe("analysisRunAccessibleName", () => {
  it("keeps the caption as kind · status · entity", () => {
    expect(analysisRunCaption(demoRun())).toBe("Lineage reconstruction · Pending · Demo Corp");
  });

  it.each([
    {
      kind: "analysis_run_tepp" as const,
      status: "analysis_status_failed" as const,
      mustInclude: "connect the measurement service",
      mustExclude: "reconstruction",
    },
    {
      kind: "analysis_run_lineage" as const,
      status: "analysis_status_failed" as const,
      mustInclude: "retry reconstruction",
      mustExclude: "measurement service",
    },
    {
      kind: "analysis_run_report" as const,
      status: "analysis_status_failed" as const,
      mustInclude: "rebuild the period report",
      mustExclude: "measurement service",
    },
    {
      kind: "analysis_run_tepp" as const,
      status: "analysis_status_pending" as const,
      mustInclude: "this is not a calibrated result",
      mustExclude: "Reconstruction",
    },
    {
      kind: "analysis_run_tepp" as const,
      status: "analysis_status_running" as const,
      mustInclude: "this is not a calibrated result",
      mustExclude: "Reconstruction",
    },
    {
      kind: "analysis_run_lineage" as const,
      status: "analysis_status_pending" as const,
      mustInclude: "Reconstruction has not started yet",
      mustExclude: "measurement",
    },
    {
      kind: "analysis_run_report" as const,
      status: "analysis_status_pending" as const,
      mustInclude: "The report has not been built yet",
      mustExclude: "Reconstruction",
    },
    {
      kind: "analysis_run_tepp" as const,
      status: "analysis_status_cancelled" as const,
      mustInclude: "cancelled before a calibrated result",
      mustExclude: "Reconstruction",
    },
  ])(
    "puts the $status $kind next action in the list name",
    ({ kind, status, mustInclude, mustExclude }) => {
      const run = demoRun({
        run_kind_code: kind,
        run_kind_label: KIND_LABEL[kind],
        status_code: status,
        status_label: STATUS_LABEL[status],
      });
      const name = analysisRunAccessibleName(run);
      const nextAction = analysisRunNextAction(run);
      expect(nextAction).toBeTruthy();
      expect(name).toBe(`Open analysis run: ${analysisRunCaption(run)}. ${nextAction}`);
      expect(name).toMatch(new RegExp(mustInclude, "i"));
      expect(name).not.toMatch(new RegExp(mustExclude));
    },
  );

  it("does not claim a calibrated result on a succeeded TEPP caption-only name", () => {
    const run = demoRun({
      run_kind_code: "analysis_run_tepp",
      run_kind_label: "TEPP measurement",
      status_code: "analysis_status_succeeded",
      status_label: "Succeeded",
    });
    expect(analysisRunNextAction(run)).toBeNull();
    expect(analysisRunAccessibleName(run)).toBe(
      "Open analysis run: TEPP measurement · Succeeded · Demo Corp",
    );
    expect(analysisRunCorpusHint(run)).toBe("These posts are the cutoff corpus this TEPP run measured.");
  });
});
