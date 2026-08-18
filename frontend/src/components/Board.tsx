import { useMemo, useState, type FormEvent } from "react";
import type { PostSummary } from "../api";
import { isoWeekCode } from "../isoWeek";
import { NewspaperCard } from "./NewspaperCard";

export const BOARD_EMPTY = "게시판에 사건이 없습니다";
export const WEEKLY_VOC_EMPTY = "이번 주 감사할 VOC가 없습니다";
export const SEARCH_EMPTY = "이 검색을 근거할 수 있는 사건이 아직 없습니다";

export type BoardProps = {
  items: PostSummary[] | null;
  error?: string | null;
  searchError?: string | null;
  onOpenItem: (postId: string) => void;
  onSearch: (query: string) => Promise<PostSummary[]>;
};

function isNewspaper(post: PostSummary): boolean {
  return Boolean(post.edition) || (post.thread_group_key ?? "").startsWith("newspaper-");
}

export function Board({ items, error, searchError, onOpenItem, onSearch }: BoardProps) {
  const [vocOnly, setVocOnly] = useState(false);
  const [week, setWeek] = useState("");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<PostSummary[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [localSearchError, setLocalSearchError] = useState<string | null>(null);

  const listed = hits ?? items;
  const visible = useMemo(() => {
    if (!listed) {
      return null;
    }
    return listed.filter((post) => {
      if (vocOnly) {
        if (isNewspaper(post) || post.voc_type_code !== "voc") {
          return false;
        }
        if (week && isoWeekCode(post.created_at) !== week) {
          return false;
        }
      }
      return true;
    });
  }, [listed, vocOnly, week]);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    const next = query.trim();
    if (!next) {
      setHits(null);
      setLocalSearchError(null);
      return;
    }
    setSearching(true);
    setLocalSearchError(null);
    try {
      setHits(await onSearch(next));
    } catch (err) {
      setLocalSearchError(String(err));
      setHits([]);
    } finally {
      setSearching(false);
    }
  }

  const newspapers = visible?.filter(isNewspaper) ?? [];
  const events = visible?.filter((post) => !isNewspaper(post)) ?? [];
  const searchFailed = Boolean(hits && hits.length === 0 && query.trim());

  return (
    <section className="popup-section lineage-home" aria-label="게시판">
      <div className="lineage-home-header">
        <h2>게시판</h2>
      </div>
      <form className="board-toolbar" onSubmit={handleSearch}>
        <label>
          <input
            type="checkbox"
            checked={vocOnly}
            onChange={(event) => setVocOnly(event.target.checked)}
          />{" "}
          주간 VOC
        </label>
        <label>
          주
          <input
            aria-label="VOC week"
            value={week}
            onChange={(event) => setWeek(event.target.value)}
            placeholder="2026-W01"
          />
        </label>
        <label>
          검색
          <input
            aria-label="Board search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ada West"
          />
        </label>
        <button type="submit" disabled={searching}>
          {searching ? "Querying..." : "검색"}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      {searchError || localSearchError ? <p className="error">{searchError ?? localSearchError}</p> : null}
      {visible === null && !error ? <p>Loading posts...</p> : null}
      {visible && visible.length === 0 && vocOnly ? (
        <p className="popup-placeholder">{WEEKLY_VOC_EMPTY}</p>
      ) : null}
      {visible && visible.length === 0 && !vocOnly && searchFailed ? (
        <p className="popup-placeholder">{SEARCH_EMPTY}</p>
      ) : null}
      {visible && visible.length === 0 && !vocOnly && !searchFailed ? (
        <p className="popup-placeholder">{BOARD_EMPTY}</p>
      ) : null}
      {newspapers.map((post) => (
        <NewspaperCard key={post.post_id} post={post} onOpen={onOpenItem} />
      ))}
      {events.length > 0 ? (
        <ul className="post-list">
          {events.map((post) => (
            <li key={post.post_id}>
              <button
                className="post-list-item"
                aria-label={`Open post: ${post.post_title}`}
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
