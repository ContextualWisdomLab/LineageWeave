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

export function FiveW1H({ slots }: { slots: FiveW1HSlot[] | null }) {
  return (
    <section className="popup-section five-w1h" aria-label={t("5W1H") }>
      <h3>{t("5W1H")}</h3>
      {slots === null ? (
        <p>{t("Loading 5W1H...")}</p>
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
                          <summary>{t("Evidence provenance")}</summary>
                          <span className="post-badge">{value.source}</span>
                          {value.ontology_codes.map((code) => (
                            <span className="post-badge" key={code}>
                              {t("Ontology class")}: {code}
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
