import type { AnalysisRun } from "../api";
import {
  analysisRunAccessibleName,
  analysisRunCaption,
  analysisRunNextAction,
} from "../analysisRunCopy";

export type AnalysisRunListButtonProps = {
  run: AnalysisRun;
  onOpen: (analysisRunId: string) => void;
};

/**
 * Home-list control for one analysis-run row (ADR 0014).
 *
 * Next action: activate the button to open the run. The accessible name
 * includes the kind-specific next-action sentence when one exists.
 */
export function AnalysisRunListButton({ run, onOpen }: AnalysisRunListButtonProps) {
  const caption = analysisRunCaption(run);
  const nextAction = analysisRunNextAction(run);
  const documentCount = run.source_counts.find(
    (count) => count.count_type_code === "analysis_count_document",
  );
  return (
    <button
      type="button"
      className="post-list-item"
      aria-label={analysisRunAccessibleName(run)}
      onClick={() => onOpen(run.analysis_run_id)}
    >
      <span className="ticket-title">{caption}</span>
      {documentCount && (
        <span className="post-badge">
          {documentCount.count_value} {documentCount.count_type_label.toLowerCase()}
        </span>
      )}
      {nextAction && <span className="post-meta">{nextAction}</span>}
    </button>
  );
}
