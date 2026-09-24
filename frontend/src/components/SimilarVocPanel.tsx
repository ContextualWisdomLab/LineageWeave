import { useContext, useEffect, useState } from "react";
import { AuthContext } from "react-oidc-context";
import "./SimilarVocPanel.css";

import type { SimilarVocItem } from "../api";
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
    <section className="similar-voc" aria-labelledby="similar-voc-heading">
      <header>
        <h3 id="similar-voc-heading">유사 VOC · 고객군 확인</h3>
        <p>같은 문제 유형으로 판정된 과거 근거와 조치 이력을 확인하세요.</p>
      </header>
      {scopedError ? (
        <StatusNotice
          kind="retry"
          message={scopedError}
          nextAction={
            retryLoadedPage
              ? hasRetainedEvidence
                ? "불러온 근거는 그대로 유지됩니다. 실패한 다음 페이지를 다시 요청하세요."
                : "실패한 다음 페이지를 다시 요청하세요."
              : "같은 조회를 다시 시도하세요."
          }
          retryLabel={retryLoadedPage ? "이전 VOC 더 불러오기 다시 시도" : "유사 VOC 다시 조회"}
          onRetry={retryAction ?? undefined}
        />
      ) : null}
      {scopedItems === null && !scopedError ? (
        <p role="status">유사 VOC 근거를 판정하고 있습니다.</p>
      ) : scopedItems?.length === 0 && !scopedError ? (
        <p role="status">같은 문제 유형으로 판정된 과거 VOC가 없습니다.</p>
      ) : scopedItems && scopedItems.length > 0 ? (
        <ol>
          {scopedItems.map((item) => (
            <li key={item.post_id}>
              <article>
                <p className="similar-voc-time">사건 시각 {new Date(item.occurred_at).toLocaleString()}</p>
                <h4>{item.post_title}</h4>
                <p>{item.issue_summary}</p>
                <p><strong>현재 글 근거</strong></p>
                <blockquote>{item.focal_evidence_text}</blockquote>
                <p><strong>과거 글 근거</strong></p>
                <blockquote>{item.candidate_evidence_text}</blockquote>
                <dl>
                  <div><dt>고객군</dt><dd>{item.customer_cohort_text ?? "동일 고객 근거 없음"}</dd></div>
                  <div><dt>과거 조치</dt><dd>{item.action_history.length ? <ul>{item.action_history.map((action) => <li key={action}>{action}</li>)}</ul> : "기록된 조치 없음"}</dd></div>
                </dl>
                <button type="button" onClick={() => onOpenPost(item.post_id)}>근거 글 열기</button>
              </article>
            </li>
          ))}
        </ol>
      ) : null}
      {scopedOnLoadMore && !retryLoadedPage ? (
        <button type="button" onClick={scopedOnLoadMore} disabled={scopedLoadingMore}>
          {scopedLoadingMore ? "이전 VOC를 불러오는 중..." : "이전 VOC 더 보기"}
        </button>
      ) : null}
    </section>
  );
}
