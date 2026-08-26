import type { OccupationalConstructAssertion } from "../api";
import {
  occupationalConstructText as text,
  type OccupationalConstructCopyKey,
} from "../occupationalConstructI18n";
import { EvidenceStatusMark } from "./EvidenceStatusMark";

export type OccupationalConstructEvidenceStatus =
  | "complete"
  | "processing"
  | "unavailable"
  | "historical_unavailable";

const FAMILY_LABEL: Record<string, OccupationalConstructCopyKey> = {
  cognitive_ability: "Cognitive ability",
  work_style: "Work style",
  work_activity: "Work activity",
  affective_reaction: "Affective reaction",
  performance_behavior: "Performance behavior",
};

/** Show evidence-bound work constructs and honest empty/provider states. */
export function OccupationalConstructEvidence({
  assertions,
  status,
}: {
  assertions: OccupationalConstructAssertion[];
  status: OccupationalConstructEvidenceStatus;
}) {
  let statusCopy: OccupationalConstructCopyKey | null = null;
  if (status === "processing") {
    statusCopy = "Work evidence is still being prepared. Reopen this record shortly.";
  } else if (status === "unavailable") {
    statusCopy = "Work evidence is unavailable. Ask an administrator to retry record analysis.";
  } else if (status === "historical_unavailable") {
    statusCopy = "Work evidence is unavailable for this historical cutoff. Review the known body instead.";
  } else if (assertions.length === 0) {
    statusCopy = "No supported work evidence was found in this record.";
  }

  return (
    <section className="popup-section" aria-labelledby="occupational-construct-heading">
      <h3 id="occupational-construct-heading">{text("Work evidence")}</h3>
      {statusCopy ? <p role="status" className="popup-placeholder">{text(statusCopy)}</p> : null}
      {status === "complete" && assertions.length > 0 ? (
        <ul className="post-evidence-list" aria-labelledby="occupational-construct-heading">
          {assertions.map((assertion) => (
            <li key={`${assertion.unit_index}:${assertion.construct_iri}`}>
              <strong>{assertion.preferred_label}</strong>{" "}
              <span className="post-badge">
                {text(FAMILY_LABEL[assertion.construct_family_code] ?? "Work evidence")}
              </span>
              <p>
                <span className="post-meta">{text("Source evidence")}: </span>
                <q>{assertion.evidence_text}</q>
              </p>
              <a
                className="citation-chip"
                href={assertion.construct_iri}
                target="_blank"
                rel="noreferrer"
              >
                {text("Open catalog definition")}
              </a>
              <details className="semantic-provenance">
                <summary>{text("Evidence details")}</summary>
                <EvidenceStatusMark status="inference" />
                {" · "}
                <span className="post-badge">
                  {text("Catalog release")}: {assertion.vocabulary_version}
                </span>
                {" · "}
                <span className="post-badge">
                  {text("Evidence unit")}: {assertion.unit_index + 1}
                </span>
              </details>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
