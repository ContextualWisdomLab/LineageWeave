import { useCallback, useEffect, useState } from "react";
import {
  fetchPostSourceResearch,
  researchPostSources,
  type PostSourceResearch,
  type SourceResearchStatus,
} from "../api";
import { ExceptionAlert } from "./SummaryStatus";
import { productExceptionCopy } from "../productExceptionCopy";
import { t, tf } from "../i18n";

const STATUS_LABEL: Record<SourceResearchStatus, string> = {
  supported: "Supported",
  refuted: "Refuted",
  not_enough_information: "Not enough information",
};

export function SourceResearchPanel({
  postId,
  accessToken,
  canResearch,
}: {
  postId: string;
  accessToken: string;
  canResearch: boolean;
}) {
  const [result, setResult] = useState<PostSourceResearch | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [researching, setResearching] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await fetchPostSourceResearch(accessToken, postId));
    } catch (err) {
      setError(productExceptionCopy(err, t("Source reference research")).title);
    } finally {
      setLoading(false);
    }
  }, [accessToken, postId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runResearch() {
    setResearching(true);
    setError(null);
    try {
      await researchPostSources(accessToken, postId);
      await load();
    } catch (err) {
      setError(productExceptionCopy(err, t("Source reference research")).title);
    } finally {
      setResearching(false);
    }
  }

  return (
    <section className="popup-section source-research" aria-labelledby="source-research-heading">
      <div className="source-research-heading">
        <div>
          <h3 id="source-research-heading">{t("Source reference research")}</h3>
          <p className="post-meta">{t("Persisted web evidence; opening this post does not run a search.")}</p>
        </div>
        {canResearch ? (
          <button type="button" onClick={() => void runResearch()} disabled={researching}>
            {researching ? t("Researching sources...") : t("Research sources")}
          </button>
        ) : null}
      </div>
      {loading ? <p role="status">{t("Loading source research...")}</p> : null}
      {error ? (
        <ExceptionAlert
          title={error}
          retryLabel={t("Retry")}
          onRetry={() => void load()}
        />
      ) : null}
      {!loading && !error && result?.research.length === 0 ? (
        <p className="popup-placeholder">{t("No persisted source research yet.")}</p>
      ) : null}
      {result?.research.length ? (
        <ol className="source-research-list">
          {result.research.map((lead) => {
            const citations = lead.retrievals.filter((item) => item.cited);
            return (
              <li key={lead.lead_ordinal}>
                <header>
                  <span className={`source-research-status is-${lead.research_status_code}`}>
                    {t(STATUS_LABEL[lead.research_status_code])}
                  </span>
                  <strong>{lead.query_text}</strong>
                </header>
                <p className="source-research-evidence">{lead.evidence_text}</p>
                <details>
                  <summary>{t("Evidence provenance")}</summary>
                  <p className="post-meta">
                    {lead.source_content_unit_id
                      ? `${t("Post body")}: ${lead.source_content_unit_id}`
                      : `${t("Image regions")}: ${lead.source_image_region_id}`}
                  </p>
                </details>
                {lead.sharing_actor_name ? (
                  <p><strong>{t("Sharing actor")}:</strong> {lead.sharing_actor_name}</p>
                ) : null}
                <p>{lead.rationale_text}</p>
                {lead.research_status_code === "not_enough_information" ? (
                  <p className="post-meta">{t("Uncertainty remains; do not infer a sharing actor from the address or URL alone.")}</p>
                ) : null}
                {citations.length ? (
                  <ul className="source-research-citations" aria-label={t("Research citations")}>
                    {citations.map((citation) => (
                      <li key={citation.url}>
                        <details>
                          <summary>{citation.title || citation.url}</summary>
                          <blockquote>{citation.passage_text}</blockquote>
                          <a
                            href={citation.url}
                            target="_blank"
                            rel="noreferrer"
                            aria-label={tf("Open source in new tab: {title}", {
                              title: citation.title || citation.url,
                            })}
                          >
                            {t("Open source")}
                          </a>
                        </details>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="post-meta">{t("No cited public evidence.")}</p>
                )}
                <p className="post-meta">
                  <strong>{t("Next action")}:</strong>{" "}
                  {t(citations.length ? "Open source" : "Review source evidence for this dimension.")}
                </p>
              </li>
            );
          })}
        </ol>
      ) : null}
    </section>
  );
}
