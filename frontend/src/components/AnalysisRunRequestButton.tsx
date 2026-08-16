export type AnalysisRunRequestButtonProps = {
  requesting: boolean;
  onRequest: () => void;
  disabled?: boolean;
};

/**
 * Records a Pending lineage run from the home Analysis runs header.
 *
 * Next action: click to capture the authorized cutoff bag. This control
 * does not start reconstruction and does not invent a TEPP score.
 */
export function AnalysisRunRequestButton({
  requesting,
  onRequest,
  disabled = false,
}: AnalysisRunRequestButtonProps) {
  return (
    <button
      type="button"
      className="keyman-select analysis-run-request"
      aria-label="Request a lineage reconstruction"
      disabled={requesting || disabled}
      onClick={onRequest}
    >
      {requesting ? "Recording the run..." : "Request a lineage reconstruction"}
    </button>
  );
}
