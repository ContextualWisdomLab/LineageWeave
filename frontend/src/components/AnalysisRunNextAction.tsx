import type { AnalysisRun } from "../api";
import {
  analysisRunCanRefresh,
  analysisRunCanStart,
  analysisRunNextAction,
  analysisRunRefreshLabel,
  analysisRunStartLabel,
} from "../analysisRunGuidance";

export function AnalysisRunNextAction({
  run,
  starting = false,
  onStart,
  onRefresh,
}: {
  run: AnalysisRun;
  starting?: boolean;
  onStart?: () => void;
  onRefresh?: () => void;
}) {
  const nextAction = analysisRunNextAction(run);
  const canStart = Boolean(onStart && analysisRunCanStart(run));
  const canRefresh = Boolean(onRefresh && analysisRunCanRefresh(run));
  const startLabel = analysisRunStartLabel(run);
  const refreshLabel = analysisRunRefreshLabel();
  if (!nextAction && !canStart && !canRefresh) {
    return null;
  }
  return (
    <div className="analysis-run-next-action">
      {nextAction ? (
        <p className="post-meta" role="status">
          {nextAction}
        </p>
      ) : null}
      {canStart ? (
        <button
          type="button"
          className="keyman-select"
          aria-label={startLabel}
          disabled={starting}
          onClick={onStart}
        >
          {starting
            ? run.run_kind_code === "analysis_run_tepp"
              ? run.status_code === "analysis_status_running"
                ? "Checking TEPP measurement status..."
                : "Submitting the TEPP request..."
              : "Reconstructing the cutoff bag..."
            : startLabel}
        </button>
      ) : null}
      {canRefresh ? (
        <button
          type="button"
          className="keyman-select"
          aria-label={refreshLabel}
          onClick={onRefresh}
        >
          {refreshLabel}
        </button>
      ) : null}
    </div>
  );
}
