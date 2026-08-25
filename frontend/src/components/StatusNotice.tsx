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
};

/**
 * One accessible notice for success, unavailable, and retry states.
 *
 * Color is never the only channel: each kind keeps a distinct glyph and
 * visible label. Callers pass already-localized message text and must not
 * interpolate provider payloads (ADR 0123).
 *
 * Success and unavailable are a named region, not `role="status"`, so they
 * do not collide with App live-region uniqueness. Retry is `role="alert"`.
 */
export function StatusNotice({
  kind,
  message,
  nextAction,
  retryLabel,
  onRetry,
}: StatusNoticeProps) {
  const label = t(KIND_LABEL_KEY[kind]);
  const description = t(KIND_DESCRIPTION_KEY[kind]);
  const showRetry = kind === "retry" && typeof onRetry === "function";
  const isRetry = kind === "retry";
  return (
    <section
      className={`status-notice status-notice-kind-${kind}`}
      role={isRetry ? "alert" : "region"}
      aria-label={`${label}: ${description}`}
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
