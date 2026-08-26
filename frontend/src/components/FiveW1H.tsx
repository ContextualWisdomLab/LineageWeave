import type { FiveW1HSlot } from "../api";
import { t } from "../i18n";

const SLOT_LABELS: Record<FiveW1HSlot["slot_code"], string> = {
  who: "Who",
  what: "What",
  when: "When",
  where: "Where",
  why: "Why",
  how: "How",
};

// Human labels for backend/app/five_w1h_ingestion.py's raw dotted-path
// evidence sources -- shown verbatim before this fix, which leaked
// internal table/column names into product UI.
const EVIDENCE_SOURCE_LABELS: Record<string, string> = {
  post_summary_role: "Extracted role",
  "post_summary_role.affiliated_organization_name": "Extracted affiliation",
  post_summary_event: "Extracted key event",
  post_summary_five_w1h: "Extracted source evidence",
  post_lineage_edge: "Linked post title",
  post_counterparty_entity: "Recorded counterparty",
};

function evidenceSourceLabel(source: string): string {
  return t(EVIDENCE_SOURCE_LABELS[source] ?? source);
}

export function FiveW1H({ slots }: { slots: FiveW1HSlot[] | null }) {
  return (
    <section className="popup-section five-w1h" aria-label={t("5W1H") }>
      <h3>{t("5W1H")}</h3>
      {slots === null ? (
        <p role="status">{t("Loading 5W1H...")}</p>
      ) : (
        <dl>
          {slots.map((slot) => (
            <div key={slot.slot_code}>
              <dt>{t(SLOT_LABELS[slot.slot_code])}</dt>
              <dd>
                {slot.values.length > 0 ? (
                  <ul>
                    {slot.values.map((value, index) => (
                      <li key={`${value.source}:${value.text}:${index}`}>
                        <strong>{value.text}</strong>
                        <details className="semantic-provenance">
                          <summary>{t("Why this item is listed")}</summary>
                          <span className="post-badge">{evidenceSourceLabel(value.source)}</span>
                          {value.evidence_text ? <span>{value.evidence_text}</span> : null}
                          {value.ontology_codes.map((code) => (
                            <span className="post-badge" key={code}>
                              {t("Category")}: {t(value.ontology_annotations.ontology_label ?? code)}
                            </span>
                          ))}
                        </details>
                      </li>
                    ))}
                  </ul>
                ) : (
                  t("No grounded evidence for this dimension.")
                )}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}
