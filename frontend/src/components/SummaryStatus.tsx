export type SummaryStatusKind = "processing" | "unavailable" | "empty";

export function SummaryStatus({
  kind,
  title,
  description,
  detail,
  retryLabel,
  onRetry,
}: {
  kind: SummaryStatusKind;
  title: string;
  description: string;
  detail?: string;
  retryLabel?: string;
  onRetry?: () => void;
}) {
  const canRetry = Boolean(onRetry && retryLabel);
  return (
    <div
      className={`popup-placeholder summary-status summary-status-${kind}`}
      role={kind === "unavailable" ? "alert" : "status"}
      aria-live={kind === "processing" ? "polite" : undefined}
    >
      <strong>{title}</strong>
      <span>{description}</span>
      {detail ? <small>{detail}</small> : null}
      {canRetry ? (
        <button type="button" onClick={onRetry}>
          {retryLabel}
        </button>
      ) : null}
    </div>
  );
}
