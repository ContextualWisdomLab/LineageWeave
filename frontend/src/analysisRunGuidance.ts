import type { AnalysisRun } from "./api";

/**
 * Home-list caption: kind · status · entity (ADR 0014).
 */
export function analysisRunCaption(run: AnalysisRun): string {
  return [run.run_kind_label, run.status_label, run.scope_entity_name ?? run.scope_kind_label]
    .filter(Boolean)
    .join(" · ");
}

/**
 * Kind-and-status exact next action. Copy and the following control must agree.
 */
export function analysisRunNextAction(run: AnalysisRun): string | null {
  switch (run.status_code) {
    case "analysis_status_pending":
      switch (run.run_kind_code) {
        case "analysis_run_lineage":
          return "Open this run, then start reconstruction. Reconstruction has not started yet.";
        case "analysis_run_tepp":
          return "Open this run to confirm which posts TEPP will measure. Measurement has not started yet — this is not a calibrated result.";
        case "analysis_run_report":
          return "Open this run to confirm which posts the period report will use. The report has not been built yet.";
        default: {
          const unexpected: never = run.run_kind_code;
          throw new Error(`unexpected analysis run kind: ${unexpected}`);
        }
      }
    case "analysis_status_failed":
      switch (run.run_kind_code) {
        case "analysis_run_tepp":
          return "Open this run to see why it failed, then connect the measurement service and re-run.";
        case "analysis_run_lineage":
          return "Open this run to see why it failed, then retry reconstruction from a current snapshot.";
        case "analysis_run_report":
          return "Open this run to see why it failed, then rebuild the period report from a current snapshot.";
        default: {
          const unexpected: never = run.run_kind_code;
          throw new Error(`unexpected analysis run kind: ${unexpected}`);
        }
      }
    case "analysis_status_running":
      switch (run.run_kind_code) {
        case "analysis_run_lineage":
          return "Refresh this run. Reconstruction is already queued on the durable outbox.";
        case "analysis_run_tepp":
          return "Refresh this run. Measurement is already queued on the durable outbox.";
        case "analysis_run_report":
          return "Refresh this run. The period report is already queued on the durable outbox.";
        default: {
          const unexpected: never = run.run_kind_code;
          throw new Error(`unexpected analysis run kind: ${unexpected}`);
        }
      }
    case "analysis_status_succeeded":
    case "analysis_status_cancelled":
    case null:
      return null;
    default: {
      const unexpected: never = run.status_code;
      throw new Error(`unexpected analysis run status: ${unexpected}`);
    }
  }
}

export function analysisRunEmptyPostsHint(run: AnalysisRun): string {
  switch (run.run_kind_code) {
    case "analysis_run_tepp":
      return (
        "No posts were available at this cutoff for TEPP to measure. " +
        "Open a later run, or ask an administrator to capture a newer snapshot."
      );
    case "analysis_run_lineage":
      return (
        "No posts were available at this cutoff for reconstruction. " +
        "Open a later run, or ask an administrator to capture a newer snapshot."
      );
    case "analysis_run_report":
      return (
        "No posts were available at this cutoff for the period report. " +
        "Open a later run, or ask an administrator to capture a newer snapshot."
      );
    default: {
      const unexpected: never = run.run_kind_code;
      throw new Error(`unexpected analysis run kind: ${unexpected}`);
    }
  }
}

export function analysisRunCorpusHint(run: AnalysisRun): string | null {
  if (run.run_kind_code !== "analysis_run_tepp") return null;
  switch (run.status_code) {
    case "analysis_status_failed":
      return (
        "These posts are the cutoff corpus TEPP would measure. Connect a TEPP " +
        "transport, then re-run, to replace Failed with a calibrated result."
      );
    case "analysis_status_succeeded":
      return "These posts are the cutoff corpus this TEPP run measured.";
    case "analysis_status_pending":
    case "analysis_status_running":
      return "These posts are the cutoff corpus TEPP will measure once this run finishes.";
    case "analysis_status_cancelled":
      return (
        "These posts are the cutoff corpus this TEPP run would have measured. " +
        "The run was cancelled before a calibrated result."
      );
    case null:
      return "These posts are the cutoff corpus attached to this TEPP run.";
    default: {
      const unexpected: never = run.status_code;
      throw new Error(`unexpected analysis run status: ${unexpected}`);
    }
  }
}

/** Start is only for a Pending lineage or TEPP row. Running work is already queued. */
export function analysisRunCanStart(run: AnalysisRun): boolean {
  return (
    (run.run_kind_code === "analysis_run_lineage" || run.run_kind_code === "analysis_run_tepp") &&
    run.status_code === "analysis_status_pending"
  );
}

export function analysisRunCanRefresh(run: AnalysisRun): boolean {
  return run.status_code === "analysis_status_running";
}

export function analysisRunStartLabel(run: AnalysisRun): string {
  return run.run_kind_code === "analysis_run_tepp"
    ? "Start TEPP measurement"
    : "Start reconstruction";
}

export function analysisRunRefreshLabel(): string {
  return "Refresh this run";
}

export function analysisRunCanRequestTeppRetry(run: AnalysisRun): boolean {
  return run.run_kind_code === "analysis_run_tepp" && run.status_code === "analysis_status_failed";
}

const REPORT_PERIOD_KEY = /^\d{4}-W\d{2}$/;

export function analysisRunReportGrouping(run: AnalysisRun): string | null {
  switch (run.scope_kind_code) {
    case "analysis_scope_corporate_entity":
      return "corporate_entity";
    case "analysis_scope_process_unit":
      return "process_unit";
    case "analysis_scope_thread_group":
      return "thread_group";
    default:
      return null;
  }
}

export function analysisRunReportGroupingKey(run: AnalysisRun): string | undefined {
  return run.scope_grouping_key || undefined;
}

/** Succeeded or failed report rows with a week key can open the rebuild surface. */
export function analysisRunReportPeriod(run: AnalysisRun): string | null {
  if (run.run_kind_code !== "analysis_run_report") {
    return null;
  }
  if (
    run.status_code !== "analysis_status_succeeded" &&
    run.status_code !== "analysis_status_failed"
  ) {
    return null;
  }
  const key = run.scope_key;
  if (!key || !REPORT_PERIOD_KEY.test(key)) {
    return null;
  }
  return key;
}
