export type CutoffWriteClockBadgeProps = {
  /** Visible mark when the live row was rewritten after the run cutoff. */
  label?: string;
};

/**
 * Marks an in-cutoff title whose live write clock is after the run.
 *
 * Next action: open the marked title and compare that live body with
 * the run cutoff before treating it as reconstructed evidence.
 */
export function CutoffWriteClockBadge({
  label = "Updated after cutoff",
}: CutoffWriteClockBadgeProps) {
  return <span className="cutoff-write-clock-badge">{label}</span>;
}
