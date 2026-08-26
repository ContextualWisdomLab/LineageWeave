import type { SourceResearchCitation } from "../api";
import { t } from "../i18n";
import "./SourceResearchPanel.css";

function judgmentLabel(code: string): string {
  if (code === "research_supported") return t("Supported by a cited public resource");
  if (code === "research_refuted") return t("Conflicts with a cited public resource");
  if (code === "research_not_enough_information") return t("Not enough public information");
  return t("Public research unavailable");
}

function leadKindLabel(code: string): string {
  return code === "research_lead_image_region"
    ? t("Image detail")
    : t("Highlighted passage");
}

function isHttpUrl(url: string | null): url is string {
  return Boolean(url && /^https?:\/\//i.test(url));
}

type Props = {
  citations: SourceResearchCitation[];
  unavailableReason?: string | null;
  canResearch?: boolean;
  researching?: boolean;
  error?: string | null;
  onResearch?: () => void;
};

/** Help the reader compare cited evidence with the relevant post content. */
export function SourceResearchPanel({
  citations,
  unavailableReason,
  canResearch = false,
  researching = false,
  error,
  onResearch,
}: Props) {
  return (
    <section className="popup-section source-research" aria-label={t("Source research")}>
      <div className="source-research-header">
        <h3>{t("Source research")}</h3>
        {canResearch && onResearch ? (
          <details className="operator-action-tools">
            <summary>{t("Evidence operations")}</summary>
            <button type="button" onClick={onResearch} disabled={researching}>
              {researching ? t("Researching...") : t("Research public sources")}
            </button>
          </details>
        ) : null}
      </div>
      <p>{t("Open the cited public resource, then compare it with the highlighted passage or image detail from this post.")}</p>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {unavailableReason ? <p role="status">{unavailableReason}</p> : null}
      {citations.length === 0 && !unavailableReason ? (
        <p role="status">{t("No public research citations yet.")}</p>
      ) : (
        <ul className="source-research-list">
          {citations.map((citation) => (
            <li
              key={`${citation.lead_kind_code}:${citation.lead_source_unit_id ?? citation.lead_image_region_id}`}
            >
              <article className="source-research-card">
                <p>{leadKindLabel(citation.lead_kind_code)}</p>
                <blockquote>{citation.lead_excerpt_text}</blockquote>
                <p>{judgmentLabel(citation.judgment_code)}</p>
                <p>{citation.rationale_text}</p>
                {isHttpUrl(citation.evidence_url) ? (
                  <p className="source-research-evidence">
                    <a href={citation.evidence_url} target="_blank" rel="noreferrer">
                      {citation.evidence_title_text || citation.evidence_url}
                    </a>
                    {citation.evidence_excerpt_text ? <span>{citation.evidence_excerpt_text}</span> : null}
                  </p>
                ) : null}
                <p>{citation.next_action_text}</p>
              </article>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
