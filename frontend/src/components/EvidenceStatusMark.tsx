import { evidenceStatusText } from "../evidenceStatusI18n";

/**
 * TEPP ADR 0016's three-tier status: directly observed, derived, or
 * forecast. A prediction is never rendered or persisted as a fact
 * (ADR 0132 decision 5).
 */
export type EvidenceStatus = "evidence" | "inference" | "prediction";

/** Glyph carries a second, non-color channel; the visible text label is the primary one. */
const STATUS_GLYPH: Record<EvidenceStatus, string> = {
  evidence: "●",
  inference: "◆",
  prediction: "△",
};

const STATUS_LABEL_KEY: Record<EvidenceStatus, "Evidence" | "Inference" | "Prediction"> = {
  evidence: "Evidence",
  inference: "Inference",
  prediction: "Prediction",
};

const STATUS_DESCRIPTION_KEY: Record<
  EvidenceStatus,
  | "Directly observed in the source record."
  | "Derived from observed evidence, not directly recorded."
  | "A forecast. Treat as unconfirmed until later evidence arrives."
> = {
  evidence: "Directly observed in the source record.",
  inference: "Derived from observed evidence, not directly recorded.",
  prediction: "A forecast. Treat as unconfirmed until later evidence arrives.",
};

/**
 * Reusable evidence / inference / prediction status badge (ADR 0132 decision
 * 5, TEPP ADR 0016). Distinguishes status by label text and glyph shape, not
 * color alone, so it remains legible without color perception (WCAG 1.4.1).
 * Presentational only -- callers supply `status` from a real TEPP-sourced
 * envelope; this component never infers or invents one.
 */
export function EvidenceStatusMark({ status }: { status: EvidenceStatus }) {
  const label = evidenceStatusText(STATUS_LABEL_KEY[status]);
  const description = evidenceStatusText(STATUS_DESCRIPTION_KEY[status]);
  return (
    <span
      className={`evidence-status-mark evidence-status-${status}`}
      role="img"
      aria-label={`${label}: ${description}`}
      title={description}
    >
      <span className="evidence-status-glyph" aria-hidden="true">
        {STATUS_GLYPH[status]}
      </span>
      {label}
    </span>
  );
}
