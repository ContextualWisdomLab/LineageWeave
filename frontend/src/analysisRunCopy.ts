import type { AnalysisRun } from "./api";
import { t, tf } from "./i18n";

/** Name a run by the customer task while retaining its governed kind in the API. */
export function analysisRunCaption(run: AnalysisRun): string {
  const kindLabel = {
    analysis_run_lineage: "Record connections",
    analysis_run_tepp: "Record measurement",
    analysis_run_topic_lineage: "Topic history",
    analysis_run_report: "Period report",
  }[run.run_kind_code];
  return [t(kindLabel), run.status_label ? t(run.status_label) : null, run.scope_entity_name ?? run.scope_kind_label]
    .filter(Boolean)
    .join(" · ");
}

/**
 * Corpus copy for a TEPP or topic-lineage run that already has cutoff posts.
 *
 * Those titles are the measurement bag, not a reconstruction result.
 * Pending or running must not claim a calibrated measurement or topic.
 */
export function analysisRunCorpusHint(run: AnalysisRun): string | null {
  const isTopicLineage = run.run_kind_code === "analysis_run_topic_lineage";
  if (run.run_kind_code !== "analysis_run_tepp" && !isTopicLineage) return null;
  const analysis = t(isTopicLineage ? "topic history" : "measurement");
  switch (run.status_code) {
    case "analysis_status_failed":
      return tf("These posts were selected for {analysis}, but this run has no result. Ask an administrator to restore analysis before requesting another run.", { analysis });
    case "analysis_status_succeeded":
      return tf("These posts were used for {analysis}. Review this run's status and available evidence.", { analysis });
    case "analysis_status_pending":
      return tf("These posts are selected for {analysis}. Start this run to request a result.", { analysis });
    case "analysis_status_running":
      return tf("These posts are selected for {analysis}. Refresh this run for the latest status.", { analysis });
    case "analysis_status_cancelled":
      return tf("These posts were selected for {analysis}, but this run was cancelled before a result was available.", { analysis });
    case null:
      return tf("These posts are selected for {analysis}. Open this run to check its status.", { analysis });
    default: {
      const unexpected: never = run.status_code;
      return unexpected;
    }
  }
}
