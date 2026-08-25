import "./SimilarVocPanel.css";

import type { SimilarVocItem } from "../api";

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
        <h3 id="similar-voc-heading">유사 VOC · 고객군 확인</h3>
        <p>같은 문제 유형으로 판정된 과거 근거와 조치 이력을 확인하세요.</p>
      </header>
      {error ? <p role="alert">{error}</p> : null}
      {items === null && !error ? (
        <p role="status">유사 VOC 근거를 판정하고 있습니다.</p>
      ) : items?.length === 0 && !error ? (
        <p role="status">같은 문제 유형으로 판정된 과거 VOC가 없습니다.</p>
      ) : items && items.length > 0 ? (
        <ol>
          {items.map((item) => (
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
      {onLoadMore ? (
        <button type="button" onClick={onLoadMore} disabled={loadingMore}>
          {loadingMore ? "이전 VOC를 불러오는 중..." : "이전 VOC 더 보기"}
        </button>
      ) : null}
    </section>
  );
}
