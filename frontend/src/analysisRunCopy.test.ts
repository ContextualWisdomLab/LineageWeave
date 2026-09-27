import { describe, expect, it } from "vitest";
import type { AnalysisRun } from "./api";
import { analysisRunCaption, analysisRunCorpusHint } from "./analysisRunCopy";

function run(kind: AnalysisRun["run_kind_code"], status: AnalysisRun["status_code"]): AnalysisRun {
  return {
    run_kind_code: kind,
    status_code: status,
    status_label: status === "analysis_status_failed" ? "Failed" : "Pending",
    scope_kind_label: "Demo workspace",
  } as AnalysisRun;
}

describe("analysis run customer copy", () => {
  it("names governed run kinds by the task", () => {
    expect(analysisRunCaption(run("analysis_run_tepp", "analysis_status_failed"))).toBe(
      "Record measurement · Failed · Demo workspace",
    );
    expect(analysisRunCaption(run("analysis_run_topic_lineage", "analysis_status_pending"))).toBe(
      "Topic history · Pending · Demo workspace",
    );
  });

  it("keeps every measurement and topic state actionable without internal boundaries", () => {
    for (const kind of ["analysis_run_tepp", "analysis_run_topic_lineage"] as const) {
      for (const status of [
        "analysis_status_pending",
        "analysis_status_running",
        "analysis_status_succeeded",
        "analysis_status_failed",
        "analysis_status_cancelled",
        null,
      ] as const) {
        const copy = analysisRunCorpusHint(run(kind, status));
        expect(copy).toBeTruthy();
        expect(copy).not.toMatch(/TEPP|transport|provider|model|worker/i);
        if (status === "analysis_status_pending") expect(copy).toContain("Start this run");
        if (status === "analysis_status_running") expect(copy).toContain("Refresh this run");
        if (status === "analysis_status_failed") expect(copy).toContain("Ask an administrator");
      }
    }
    expect(analysisRunCorpusHint(run("analysis_run_lineage", "analysis_status_pending"))).toBeNull();
  });
});
