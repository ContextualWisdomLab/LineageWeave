/** Offer a safe next action after the browser sign-in callback fails. */
export function SignInRecovery({
  brandName,
  message,
  actionLabel,
  onRetry,
}: {
  brandName: string;
  message: string;
  actionLabel: string;
  onRetry: () => void;
}) {
  return (
    <div className="app-shell">
      <main className="login-screen">
        <div className="login-card">
          <div className="login-header">
            <h1>{brandName}</h1>
            <p className="login-subtitle">Marketing & Operational Lineage Intelligence</p>
          </div>
          <div className="login-controls">
            <p className="error" role="alert">{message}</p>
            <button className="btn-primary" onClick={onRetry}>{actionLabel}</button>
          </div>
        </div>
      </main>
    </div>
  );
}
