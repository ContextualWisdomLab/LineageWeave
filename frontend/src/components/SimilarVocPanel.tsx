import { useContext, useEffect, useId, useState } from "react";
import { AuthContext } from "react-oidc-context";
import "./SimilarVocPanel.css";

import type { SimilarVocItem } from "../api";
import { t, tf } from "../i18n";
import { StatusNotice } from "./StatusNotice";

type Props = {
  sourcePostId?: string;
  items: SimilarVocItem[] | null;
  error?: string | null;
  onOpenPost: (postId: string) => void;
  onLoadMore?: (() => void) | null;
  onRetry?: (() => void) | null;
  loadingMore?: boolean;
};

type DisplayScope = {
  sourcePostId?: string;
  authorizationScope: string | null;
};

/** Shows semantically adjudicated prior VOCs and their source-supported actions. */
export function SimilarVocPanel({ sourcePostId, items, error, onOpenPost, onLoadMore, onRetry, loadingMore = false }: Props) {
  const headingId = useId();
  const auth = useContext(AuthContext);
  const authorizationScope = auth?.user?.access_token ?? null;
  const [displayedScope, setDisplayedScope] = useState<DisplayScope>(() => ({
    sourcePostId,
    authorizationScope,
  }));

  const displayScopeIsCurrent =
    displayedScope.sourcePostId === sourcePostId &&
    displayedScope.authorizationScope === authorizationScope;

  useEffect(() => {
    if (items === null && !displayScopeIsCurrent) {
      setDisplayedScope({ sourcePostId, authorizationScope });
    }
  }, [authorizationScope, displayScopeIsCurrent, items, sourcePostId]);

  const scopedItems = displayScopeIsCurrent ? items : null;
  const scopedError = displayScopeIsCurrent ? error : null;
  const scopedOnLoadMore = displayScopeIsCurrent ? onLoadMore : null;
  const scopedLoadingMore = displayScopeIsCurrent && loadingMore;
  const retryLoadedPage = Boolean(scopedError && scopedOnLoadMore);
  const hasRetainedEvidence = Boolean(scopedItems && scopedItems.length > 0);
  const retryAction = retryLoadedPage ? scopedOnLoadMore : onRetry;

  return (
    <section className="similar-voc" aria-labelledby={headingId}>
      <header>
        <h3 id={headingId}>{t("Similar VOC · customer cohort check")}</h3>
        <p>{t("Review prior evidence and action history adjudicated under the same issue type.")}</p>
      </header>
      {scopedError ? (
        <StatusNotice
          kind="retry"
          message={scopedError}
          nextAction={
            retryLoadedPage
              ? hasRetainedEvidence
                ? t("Loaded evidence stays visible. Request the failed next page again.")
                : t("Request the failed next page again.")
              : t("Try the same lookup again.")
          }
          retryLabel={retryLoadedPage ? t("Retry loading more prior VOC") : t("Look up similar VOC again")}
          onRetry={retryAction ?? undefined}
        />
      ) : null}
      {scopedItems === null && !scopedError ? (
        <p role="status">{t("Adjudicating similar VOC evidence.")}</p>
      ) : scopedItems?.length === 0 && !scopedError ? (
        <p role="status">{t("No prior VOC adjudicated under the same issue type.")}</p>
      ) : scopedItems && scopedItems.length > 0 ? (
        <ol>
          {scopedItems.map((item) => (
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
      {scopedOnLoadMore && !retryLoadedPage ? (
        <button type="button" onClick={scopedOnLoadMore} disabled={scopedLoadingMore}>
          {scopedLoadingMore ? t("Loading more prior VOC...") : t("Show more prior VOC")}
        </button>
      ) : null}
    </section>
  );
}
