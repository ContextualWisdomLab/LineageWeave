import type { AnalysisRun, AnalysisRunKindCode, AnalysisRunStatusCode } from "./api";

/**
 * Visible list caption. Kind, status, and entity stay in this order
 * (ADR 0014). The machine `failure_code` stays off this string.
 */
export function analysisRunCaption(run: AnalysisRun): string {
  return [run.run_kind_label, run.status_label, run.scope_entity_name ?? run.scope_kind_label]
    .filter(Boolean)
    .join(" · ");
}

function unexpectedKindNextAction(
  unexpected: never,
  failed: boolean,
): string {
  void unexpected;
  return failed
    ? "Open this run to see why it failed, then retry from a current snapshot."
    : "Open this run to confirm its next step. The registered kind is not lineage, TEPP, or a period report.";
}

function pendingNextAction(kind: AnalysisRunKindCode): string {
  switch (kind) {
    case "analysis_run_lineage":
      return "Open this run to confirm which posts it will use. Reconstruction has not started yet.";
    case "analysis_run_tepp":
      return "Open this run to confirm which posts TEPP will measure. Measurement has not started yet — this is not a calibrated result.";
    case "analysis_run_report":
      return "Open this run to confirm which posts the period report will use. The report has not been built yet.";
    default:
      return unexpectedKindNextAction(kind, false);
  }
}

function failedNextAction(kind: AnalysisRunKindCode): string {
  switch (kind) {
    case "analysis_run_tepp":
      return "Open this run to see why it failed, then connect the measurement service and re-run.";
    case "analysis_run_lineage":
      return "Open this run to see why it failed, then retry reconstruction from a current snapshot.";
    case "analysis_run_report":
      return "Open this run to see why it failed, then rebuild the period report from a current snapshot.";
    default:
      return unexpectedKindNextAction(kind, true);
  }
}

function runningNextAction(kind: AnalysisRunKindCode): string {
  switch (kind) {
    case "analysis_run_lineage":
      return "Open this run to confirm which posts reconstruction is using. Reconstruction has not finished yet.";
    case "analysis_run_tepp":
      return "Open this run to confirm which posts TEPP is measuring. Measurement is in progress — this is not a calibrated result.";
    case "analysis_run_report":
      return "Open this run to confirm which posts the period report is using. The report has not been built yet.";
    default:
      return unexpectedKindNextAction(kind, false);
  }
}

function cancelledNextAction(kind: AnalysisRunKindCode): string {
  switch (kind) {
    case "analysis_run_lineage":
      return "This run was cancelled before reconstruction finished. Request a new reconstruction from a current snapshot.";
    case "analysis_run_tepp":
      return "This run was cancelled before a calibrated result. Connect the measurement service, then re-run.";
    case "analysis_run_report":
      return "This run was cancelled before the period report was built. Rebuild the period report from a current snapshot.";
    default:
      return unexpectedKindNextAction(kind, true);
  }
}

/**
 * Next action for the home list and detail (ADR 0014).
 *
 * The machine `failure_code` stays on detail history. Copy is pinned to
 * registered kinds so a pending or running TEPP row is not mistaken for
 * reconstruction, and a failed lineage row is not mistaken for a missing
 * TEPP transport. Unknown wire codes stay off the sentence.
 */
export function analysisRunNextAction(run: AnalysisRun): string | null {
  const status: AnalysisRunStatusCode | null = run.status_code;
  switch (status) {
    case "analysis_status_pending":
      return pendingNextAction(run.run_kind_code);
    case "analysis_status_failed":
      return failedNextAction(run.run_kind_code);
    case "analysis_status_running":
      return runningNextAction(run.run_kind_code);
    case "analysis_status_cancelled":
      return cancelledNextAction(run.run_kind_code);
    case "analysis_status_succeeded":
    case null:
      return null;
    default: {
      const unexpected: never = status;
      void unexpected;
      return "Open this run to confirm its current status before acting.";
    }
  }
}

/**
 * List-button accessible name (WCAG 2.2 SC 4.1.2 / AccName 1.1).
 *
 * `aria-label` replaces the button contents, so the next-action sentence
 * must be in the name or a screen reader only hears the caption.
 */
export function analysisRunAccessibleName(run: AnalysisRun): string {
  const caption = analysisRunCaption(run);
  const nextAction = analysisRunNextAction(run);
  return nextAction ? `Open analysis run: ${caption}. ${nextAction}` : `Open analysis run: ${caption}`;
}

/**
 * Empty-corpus copy that tells the operator what to do next.
 */
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
      void unexpected;
      return (
        "No posts were available at this cutoff. Open a later run, or ask an " +
        "administrator to capture a newer snapshot."
      );
    }
  }
}

/**
 * Corpus copy for a TEPP run that already has cutoff posts.
 *
 * Those titles are the measurement bag, not a reconstruction result.
 * Pending or running must not claim a calibrated measurement.
 */
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
      void unexpected;
      return "These posts are the cutoff corpus attached to this TEPP run.";
    }
  }
}

/**
 * Next action when a cutoff title opens the live post (ADR 0016).
 *
 * Post-body versioning is a later slice. Until then the operator must
 * compare the opened body with this run's cutoff instead of treating
 * today's text as reconstructed evidence.
 */
export function analysisRunLivePostWarning(cutoffIso: string): string {
  const cutoffDate = cutoffIso.slice(0, 10);
  return (
    `Opening a title shows the live post. Compare it with cutoff ${cutoffDate} ` +
    "before you treat the body as reconstructed evidence — it may have changed after this run."
  );
}

export function analysisRunLivePostButtonLabel(postTitle: string): string {
  return `Open live post (may have changed after cutoff): ${postTitle}`;
}
