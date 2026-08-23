import { describe, expect, it } from "vitest";
import type { AnalysisRun } from "./api";
import {
  analysisRunCanRequestTeppRetry,
  analysisRunCanRefresh,
  analysisRunCanStart,
  analysisRunCaption,
  analysisRunCorpusHint,
  analysisRunEmptyPostsHint,
  analysisRunNextAction,
  analysisRunRefreshLabel,
  analysisRunReportGrouping,
  analysisRunReportGroupingKey,
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
  it("summarizes each run kind without inventing a missing entity", () => {
    const lineage = run({
      run_kind_code: "analysis_run_lineage",
      status_code: "analysis_status_pending",
    });
    expect(analysisRunCaption(lineage)).toBe("Lineage reconstruction · Status · Demo Corp");
    expect(analysisRunCaption({ ...lineage, scope_entity_name: undefined })).toBe(
      "Lineage reconstruction · Status · Corporate entity",
    );
    expect(analysisRunEmptyPostsHint(lineage)).toMatch(/reconstruction/i);
    expect(analysisRunEmptyPostsHint({ ...lineage, run_kind_code: "analysis_run_tepp" })).toMatch(/TEPP/);
    expect(analysisRunEmptyPostsHint({ ...lineage, run_kind_code: "analysis_run_report" })).toMatch(/period report/i);
  });

  it("describes the TEPP cutoff corpus for every lifecycle state", () => {
    const tepp = run({ run_kind_code: "analysis_run_tepp", status_code: "analysis_status_pending" });
    expect(analysisRunCorpusHint({ ...tepp, run_kind_code: "analysis_run_lineage" })).toBeNull();
    expect(analysisRunCorpusHint({ ...tepp, status_code: "analysis_status_failed" })).toMatch(/connect/i);
    expect(analysisRunCorpusHint({ ...tepp, status_code: "analysis_status_succeeded" })).toMatch(/measured/i);
    expect(analysisRunCorpusHint(tepp)).toMatch(/will measure/i);
    expect(analysisRunCorpusHint({ ...tepp, status_code: "analysis_status_running" })).toMatch(/will measure/i);
    expect(analysisRunCorpusHint({ ...tepp, status_code: "analysis_status_cancelled" })).toMatch(/cancelled/i);
    expect(analysisRunCorpusHint({ ...tepp, status_code: null })).toMatch(/attached/i);
  });

  it("maps report scope and period only when the persisted run can open a report", () => {
    const report = run({ run_kind_code: "analysis_run_report", status_code: "analysis_status_succeeded" });
    expect(analysisRunReportGrouping(report)).toBe("corporate_entity");
    expect(analysisRunReportGrouping({ ...report, scope_kind_code: "analysis_scope_process_unit" })).toBe("process_unit");
    expect(analysisRunReportGrouping({ ...report, scope_kind_code: "analysis_scope_thread_group" })).toBe("thread_group");
    expect(analysisRunReportGrouping({ ...report, scope_kind_code: "unsupported" })).toBeNull();
    expect(analysisRunReportGroupingKey({ ...report, scope_grouping_key: "group-1" })).toBe("group-1");
    expect(analysisRunReportGroupingKey({ ...report, scope_grouping_key: "" })).toBeUndefined();
    expect(analysisRunReportPeriod({ ...report, run_kind_code: "analysis_run_lineage" })).toBeNull();
    expect(analysisRunReportPeriod({ ...report, status_code: "analysis_status_pending" })).toBeNull();
    expect(analysisRunReportPeriod({ ...report, scope_key: "2026-02" })).toBeNull();
    expect(analysisRunReportPeriod({ ...report, scope_key: undefined })).toBeNull();
  });

  it("keeps start, refresh, retry, and remaining lifecycle actions kind-specific", () => {
    const pendingLineage = run({ run_kind_code: "analysis_run_lineage", status_code: "analysis_status_pending" });
    const pendingReport = run({ run_kind_code: "analysis_run_report", status_code: "analysis_status_pending" });
    const runningReport = run({ run_kind_code: "analysis_run_report", status_code: "analysis_status_running" });
    expect(analysisRunNextAction(pendingLineage)).toMatch(/start reconstruction/i);
    expect(analysisRunNextAction(pendingReport)).toMatch(/report has not been built/i);
    expect(analysisRunNextAction(runningReport)).toMatch(/already queued/i);
    expect(analysisRunNextAction({ ...pendingLineage, status_code: "analysis_status_cancelled" })).toBeNull();
    expect(analysisRunNextAction({ ...pendingLineage, status_code: null })).toBeNull();
    expect(analysisRunStartLabel(pendingLineage)).toBe("Start reconstruction");
    expect(analysisRunRefreshLabel()).toBe("Refresh this run");
    expect(analysisRunCanRequestTeppRetry({ ...pendingLineage, run_kind_code: "analysis_run_tepp", status_code: "analysis_status_failed" })).toBe(true);
    expect(analysisRunCanRequestTeppRetry(pendingLineage)).toBe(false);
  });

  it("fails closed when the backend returns an unknown kind or status", () => {
    const pending = run({ run_kind_code: "analysis_run_lineage", status_code: "analysis_status_pending" });
    const unknownKind = { ...pending, run_kind_code: "unknown_kind" } as unknown as AnalysisRun;
    const unknownStatus = { ...pending, status_code: "unknown_status" } as unknown as AnalysisRun;

    expect(() => analysisRunNextAction(unknownKind)).toThrow("unexpected analysis run kind");
    expect(() => analysisRunNextAction({ ...unknownKind, status_code: "analysis_status_failed" })).toThrow(
      "unexpected analysis run kind",
    );
    expect(() => analysisRunNextAction({ ...unknownKind, status_code: "analysis_status_running" })).toThrow(
      "unexpected analysis run kind",
    );
    expect(() => analysisRunNextAction(unknownStatus)).toThrow("unexpected analysis run status");
    expect(() => analysisRunEmptyPostsHint(unknownKind)).toThrow("unexpected analysis run kind");
    expect(() => analysisRunCorpusHint({ ...unknownStatus, run_kind_code: "analysis_run_tepp" })).toThrow(
      "unexpected analysis run status",
    );
  });

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
