import "./SimilarVocPanel.css";

import type { SimilarVocItem } from "../api";
import { t, tf } from "../i18n";

type Props = {
  items: SimilarVocItem[] | null;
  error?: string | null;
  onOpenPost: (postId: string) => void;
  onLoadMore?: (() => void) | null;
  loadingMore?: boolean;
};

/** Shows semantically adjudicated prior VOCs and their source-supported actions. */
export function SimilarVocPanel({ items, error, onOpenPost, onLoadMore, loadingMore = false }: Props) {
  return (
    <section className="similar-voc" aria-labelledby="similar-voc-heading">
      <header>
        <h3 id="similar-voc-heading">{t("Similar VOC · customer cohort check")}</h3>
        <p>{t("Review prior evidence and action history adjudicated under the same issue type.")}</p>
      </header>
      {error ? <p role="alert">{error}</p> : null}
      {items === null && !error ? (
        <p role="status">{t("Adjudicating similar VOC evidence.")}</p>
      ) : items?.length === 0 && !error ? (
        <p role="status">{t("No prior VOC adjudicated under the same issue type.")}</p>
      ) : items && items.length > 0 ? (
        <ol>
          {items.map((item) => (
            <li key={item.post_id}>
              <article>
                <p className="similar-voc-time">{tf("Event time {time}", { time: new Date(item.occurred_at).toLocaleString() })}</p>
                <h4>{item.post_title}</h4>
                <p>{item.issue_summary}</p>
                <p><strong>{t("Current post evidence")}</strong></p>
                <blockquote>{item.focal_evidence_text}</blockquote>
                <p><strong>{t("Prior post evidence")}</strong></p>
                <blockquote>{item.candidate_evidence_text}</blockquote>
                <dl>
                  <div><dt>{t("Customer cohort")}</dt><dd>{item.customer_cohort_text ?? t("No shared customer evidence")}</dd></div>
                  <div><dt>{t("Prior action")}</dt><dd>{item.action_history.length ? <ul>{item.action_history.map((action) => <li key={action}>{action}</li>)}</ul> : t("No recorded action")}</dd></div>
                </dl>
                <button type="button" onClick={() => onOpenPost(item.post_id)}>{t("Open evidence post")}</button>
              </article>
            </li>
          ))}
        </ol>
      ) : null}
      {onLoadMore ? (
        <button type="button" onClick={onLoadMore} disabled={loadingMore}>
          {loadingMore ? t("Loading more prior VOC...") : t("Show more prior VOC")}
        </button>
      ) : null}
    </section>
  );
}
