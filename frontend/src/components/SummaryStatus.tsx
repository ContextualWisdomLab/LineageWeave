import { t } from "../i18n";

export type SummaryStatusKind = "processing" | "unavailable" | "empty";
export type SummaryStatusVariant = "block" | "inline";

export function SummaryStatus({
  kind,
  title,
  description,
  detail,
  retryLabel,
  onRetry,
  variant = "block",
}: {
  kind: SummaryStatusKind;
  title: string;
  description: string;
  detail?: string;
  retryLabel?: string;
  onRetry?: () => void;
  variant?: SummaryStatusVariant;
}) {
  const canRetry = Boolean(onRetry && retryLabel);
  const className = [
    "popup-placeholder",
    "summary-status",
    `summary-status-${kind}`,
    variant === "inline" ? "summary-status-inline" : null,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div
      className={className}
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

export function ExceptionAlert({
  title,
  description,
  retryLabel,
  onRetry,
  variant = "block",
}: {
  title: string;
  description?: string;
  retryLabel?: string;
  onRetry?: () => void;
  variant?: SummaryStatusVariant;
}) {
  return (
    <SummaryStatus
      kind="unavailable"
      title={title}
      description={description ?? t("Retry, or continue with saved evidence.")}
      retryLabel={retryLabel}
      onRetry={onRetry}
      variant={variant}
    />
  );
}
