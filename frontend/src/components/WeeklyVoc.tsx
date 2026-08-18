import type { PostSummary } from "../api";

export const WEEKLY_VOC_EMPTY = "이번 주 감사할 VOC가 없습니다";

export type WeeklyVocProps = {
  items: PostSummary[] | null;
  error?: string | null;
  onOpenItem: (postId: string) => void;
};

export function WeeklyVoc({ items, error, onOpenItem }: WeeklyVocProps) {
  return (
    <section className="popup-section lineage-home" aria-label="주간 VOC">
      <div className="lineage-home-header">
        <h2>주간 VOC</h2>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {items === null && !error ? <p>Loading posts...</p> : null}
      {items && items.length === 0 ? (
        <p className="popup-placeholder">{WEEKLY_VOC_EMPTY}</p>
      ) : null}
      {items && items.length > 0 ? (
        <ul className="post-list">
          {items.map((post) => (
            <li key={post.post_id}>
              <button
                className="post-list-item"
                aria-label={`Open VOC item: ${post.post_title}`}
                onClick={() => onOpenItem(post.post_id)}
              >
                <span className="post-title">{post.post_title}</span>
                <span className="post-badge">{post.voc_type_label ?? post.voc_type_code}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
