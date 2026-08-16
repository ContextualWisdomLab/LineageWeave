export type StatusAlertProps = {
  children: string;
};

/**
 * Announces a fail-closed status so the operator hears the next action.
 *
 * Next action: read the sentence, then use the control it names
 * (open a visible run, or request a lineage reconstruction).
 */
export function StatusAlert({ children }: StatusAlertProps) {
  return (
    <p className="status-alert" role="alert">
      {children}
    </p>
  );
}
