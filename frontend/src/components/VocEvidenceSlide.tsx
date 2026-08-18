import { useState } from "react";
import type { VocEvidence } from "../api";

export const VOC_EVIDENCE_EMPTY = "이 글의 VOC 근거를 아직 받을 수 없습니다";

export type VocEvidenceSlideProps = {
  evidence: VocEvidence | null;
  error?: string | null;
};

export function VocEvidenceSlide({ evidence, error }: VocEvidenceSlideProps) {
  const [open, setOpen] = useState(false);
  const excerpts = evidence?.excerpts ?? [];
  const counterparties = evidence?.counterparties ?? [];
  const empty = evidence !== null && excerpts.length === 0 && counterparties.length === 0;

  return (
    <section className="popup-section" aria-label="VOC 근거">
      <h3>VOC 근거</h3>
      {error ? <p className="error">{error}</p> : null}
      {evidence === null && !error ? <p>Loading VOC evidence...</p> : null}
      {empty ? <p className="popup-placeholder">{VOC_EVIDENCE_EMPTY}</p> : null}
      {evidence && !empty ? (
        <p>
          <button type="button" onClick={() => setOpen(true)}>
            VOC 근거 열기
          </button>
        </p>
      ) : null}
      {open && evidence && !empty ? (
        <aside className="evidence-panel" aria-label="VOC 근거 슬라이드">
          <button type="button" onClick={() => setOpen(false)}>
            VOC 근거 닫기
          </button>
          <p>{evidence.voc_type_label}</p>
          {excerpts.length > 0 ? (
            <ul>
              {excerpts.map((excerpt) => (
                <li key={excerpt}>{excerpt}</li>
              ))}
            </ul>
          ) : null}
          {counterparties.length > 0 ? (
            <ul>
              {counterparties.map((row) => (
                <li key={`${row.counterparty_entity_name}:${row.relationship_type_code}`}>
                  {row.relationship_label} · {row.counterparty_entity_name}
                </li>
              ))}
            </ul>
          ) : null}
        </aside>
      ) : null}
    </section>
  );
}
