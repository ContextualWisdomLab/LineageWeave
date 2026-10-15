import { t } from "../i18n";

/** Shared token-backed next-action notice (ADR 0220). */
export type StatusNoticeKind = "success" | "unavailable" | "retry";

const KIND_GLYPH: Record<StatusNoticeKind, string> = {
  success: "●",
  unavailable: "◌",
  retry: "△",
};

const KIND_LABEL_KEY: Record<StatusNoticeKind, string> = {
  success: "Ready",
  unavailable: "Unavailable",
  retry: "Retry needed",
};

const KIND_DESCRIPTION_KEY: Record<StatusNoticeKind, string> = {
  success: "This evidence is ready to use.",
  unavailable: "This evidence is unavailable. Follow the next action.",
  retry: "This request failed. Retry the same action.",
};

export type StatusNoticeProps = {
  kind: StatusNoticeKind;
  message: string;
  nextAction?: string;
  retryLabel?: string;
  onRetry?: () => void;
  announce?: boolean;
};

/**
 * One accessible notice for success, unavailable, and retry states.
 *
 * Color is never the only channel: each kind keeps a distinct glyph and
 * visible label. Callers pass already-localized message text and must not
 * interpolate provider payloads (ADR 0123).
 *
 * Success and unavailable are named regions by default, avoiding App
 * live-region collisions. Retry and explicitly announced results are alerts.
 */
export function StatusNotice({
  kind,
  message,
  nextAction,
  retryLabel,
  onRetry,
  announce = false,
}: StatusNoticeProps) {
  const label = t(KIND_LABEL_KEY[kind]);
  const description = t(KIND_DESCRIPTION_KEY[kind]);
  const showRetry = kind === "retry" && typeof onRetry === "function";
  const isAlert = kind === "retry" || (kind === "unavailable" && announce);
  return (
    <section
      className={`status-notice status-notice-kind-${kind}`}
      role={isAlert ? "alert" : "region"}
      aria-label={isAlert ? undefined : `${label}: ${description}`}
    >
      <p className="status-notice-heading">
        <span className="status-notice-glyph" aria-hidden="true">
          {KIND_GLYPH[kind]}
        </span>
        {label}
      </p>
      <p className="status-notice-message">{message}</p>
      {nextAction ? <p className="status-notice-next-action">{nextAction}</p> : null}
      {showRetry ? (
        <button type="button" className="btn-secondary status-notice-retry" onClick={onRetry}>
          {retryLabel ?? t("Retry")}
        </button>
      ) : null}
    </section>
  );
}
