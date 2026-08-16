import type { AnalysisRun } from "./api";

/**
 * Home-list caption: kind · status · entity (ADR 0014).
 *
 * Next action: read the caption, then open that row.
 */
export function analysisRunCaption(run: AnalysisRun): string {
  return [run.run_kind_label, run.status_label, run.scope_entity_name ?? run.scope_kind_label]
    .filter(Boolean)
    .join(" · ");
}

/**
 * Next action for a pending or failed run on the home list and detail.
 *
 * The machine `failure_code` stays on detail history (ADR 0014). Copy
 * is pinned to registered kinds so a pending TEPP row is not mistaken
 * for reconstruction, and a failed lineage row is not mistaken for a
 * missing TEPP transport.
 */
export function analysisRunNextAction(run: AnalysisRun): string | null {
  switch (run.status_code) {
    case "analysis_status_pending":
      switch (run.run_kind_code) {
        case "analysis_run_lineage":
          return "Open this run to confirm which posts it will use. Reconstruction has not started yet.";
        case "analysis_run_tepp":
          return "Open this run to confirm which posts TEPP will measure. Measurement has not started yet — this is not a calibrated result.";
        case "analysis_run_report":
          return "Open this run to confirm which posts the period report will use. The report has not been built yet.";
        default: {
          const unexpected: never = run.run_kind_code;
          return unexpected;
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
          return unexpected;
        }
      }
    case "analysis_status_running":
    case "analysis_status_succeeded":
    case "analysis_status_cancelled":
    case null:
      return null;
    default: {
      const unexpected: never = run.status_code;
      return unexpected;
    }
  }
}

/**
 * Document-count badge for one home-list row.
 *
 * Next action: use the count to decide whether the cutoff bag is empty
 * before opening the run.
 */
export function analysisRunDocumentCountLabel(run: AnalysisRun): string | undefined {
  const documentCount = run.source_counts.find(
    (count) => count.count_type_code === "analysis_count_document",
  );
  if (!documentCount) {
    return undefined;
  }
  return `${documentCount.count_value} ${documentCount.count_type_label.toLowerCase()}`;
}
