import "./SimilarVocPanel.css";

export type SimilarVocItem = {
  post_id: string;
  post_title: string;
  issue_summary: string;
  candidate_evidence_text: string;
  customer_cohort_text: string | null;
  action_history: string[];
  fused_rank: number;
};

type Props = {
  items: SimilarVocItem[];
  onOpenPost: (postId: string) => void;
};

/** Shows semantically adjudicated prior VOCs and their source-supported actions. */
export function SimilarVocPanel({ items, onOpenPost }: Props) {
  return (
    <section className="similar-voc" aria-labelledby="similar-voc-heading">
      <header>
        <h3 id="similar-voc-heading">유사 VOC · 고객군 확인</h3>
        <p>같은 문제 유형으로 판정된 과거 근거와 조치 이력을 확인하세요.</p>
      </header>
      {items.length === 0 ? (
        <p role="status">같은 문제 유형으로 판정된 과거 VOC가 없습니다.</p>
      ) : (
        <ol>
          {items.map((item) => (
            <li key={item.post_id}>
              <article>
                <p className="similar-voc-rank">추천 {item.fused_rank}</p>
                <h4>{item.post_title}</h4>
                <p>{item.issue_summary}</p>
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
      )}
    </section>
  );
}
