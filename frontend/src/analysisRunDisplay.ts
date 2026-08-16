import type { AnalysisRun } from "./api";

/**
 * Buyer-facing caption for one authorized analysis run.
 *
 * Combines kind, latest status, and scope so the home list tells the
 * operator which reconstruction they are about to open.
 */
export function analysisRunCaption(run: AnalysisRun): string {
  return [run.run_kind_label, run.status_label, run.scope_entity_name ?? run.scope_kind_label]
    .filter(Boolean)
    .join(" · ");
}

/**
 * Shorten a reproducibility digest for the home detail.
 *
 * Full SHA values stay on the API payload; the UI shows enough prefix
 * to compare against an approved revision without dumping a raw hash.
 */
export function shortDigest(value: string | undefined, length = 12): string | null {
  if (!value) return null;
  return value.slice(0, length);
}

/**
 * Next action for a failed run on the home list.
 *
 * The machine `failure_code` stays on detail history (ADR 0014). The
 * list tells the operator to open the run, then reconnect the service.
 */
export function analysisRunNextAction(run: AnalysisRun): string | null {
  if (run.status_code === "analysis_status_failed") {
    return "Open this run to see why it failed, then connect the measurement service and re-run.";
  }
  return null;
}

/**
 * Empty-corpus copy that tells the operator what to do next.
 */
export function analysisRunEmptyPostsHint(run: AnalysisRun): string {
  if (run.run_kind_code === "analysis_run_tepp") {
    return (
      "No posts were available at this cutoff for TEPP to measure. " +
      "Open a later run, or ask an administrator to capture a newer snapshot."
    );
  }
  return (
    "No posts were available at this cutoff. Open a later run, or ask an " +
    "administrator to capture a newer snapshot."
  );
}

/**
 * Corpus copy for a TEPP run that already has cutoff posts.
 *
 * Those titles are the measurement bag, not a reconstruction result.
 */
export function analysisRunCorpusHint(run: AnalysisRun): string | null {
  if (run.run_kind_code !== "analysis_run_tepp") return null;
  return (
    "These posts are the cutoff corpus TEPP would measure. Connect a TEPP " +
    "transport, then re-run, to replace Failed with a calibrated result."
  );
}
