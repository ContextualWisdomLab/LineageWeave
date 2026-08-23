import { t } from "../i18n";

export type AuthErrorScreenProps = {
  /** Brand name shown in the header, matching the normal login screen. */
  brandName: string;
  /** Raw error message from the auth provider (e.g. Keycloak's "Token is not active"). */
  message: string;
  /** Starts a fresh sign-in, preserving the return URL. */
  onRetry: () => void;
};

const SESSION_TOKEN_PATTERN = /token|session/i;
const SESSION_EXPIRED_REASON_PATTERN = /expired|inactive|not active|invalid/i;

/**
 * Shown when the OIDC provider reports an auth error -- most commonly an
 * expired/invalid session token. Session expiry is a routine, recoverable
 * condition, not a fatal one: it gets the same login-card treatment as the
 * normal login screen, with the raw provider detail kept as diagnostic-only
 * text instead of being dumped as the entire page.
 */
export function AuthErrorScreen({ brandName, message, onRetry }: AuthErrorScreenProps) {
  const isSessionExpired =
    SESSION_TOKEN_PATTERN.test(message) && SESSION_EXPIRED_REASON_PATTERN.test(message);
  return (
    <div className="app-shell">
      <main className="login-screen">
        <div className="login-card">
          <div className="login-header">
            <h1>{brandName}</h1>
            <p className="login-subtitle" role="alert">
              {isSessionExpired
                ? t("Your session has expired.")
                : t("An authentication error occurred.")}
            </p>
          </div>
          <div className="login-controls">
            <button className="btn-primary" onClick={onRetry}>
              {t("Log in again")}
            </button>
          </div>
          <p className="login-help error" aria-label={t("Technical detail")}>
            {message}
          </p>
        </div>
      </main>
    </div>
  );
}
