export type AnalysisRunListButtonProps = {
  caption: string;
  nextAction?: string | null;
  documentCountLabel?: string;
  onOpen: () => void;
};

/**
 * Opens one analysis-run row from the home list.
 *
 * Next action: click the caption to confirm the cutoff posts. Pending
 * TEPP copy must not claim a calibrated measurement.
 */
export function AnalysisRunListButton({
  caption,
  nextAction,
  documentCountLabel,
  onOpen,
}: AnalysisRunListButtonProps) {
  return (
    <button
      type="button"
      className="post-list-item analysis-run-list-button"
      aria-label={`Open analysis run: ${caption}`}
      onClick={onOpen}
    >
      <span className="ticket-title">{caption}</span>
      {documentCountLabel ? <span className="post-badge">{documentCountLabel}</span> : null}
      {nextAction ? <span className="post-meta">{nextAction}</span> : null}
    </button>
  );
}
