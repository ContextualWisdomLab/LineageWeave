import type { LineageGraph, LinkedPostRef, PostLineage } from "../api";
import { LineageDag } from "../LineageDag";
import { subgraphForPost } from "../lineageLayout";

export const EVENT_LINEAGE_EMPTY = "연결된 사건이 없습니다";

export type EventLineagePanelProps = {
  lineage: PostLineage | null;
  graph: LineageGraph | null;
  postId: string;
  onSelectNode?: (postId: string) => void;
};

function LineageLink({
  post,
  kind,
  onSelectNode,
}: {
  post: LinkedPostRef;
  kind: "direct" | "indirect";
  onSelectNode?: (postId: string) => void;
}) {
  return (
    <li className={`lineage-link lineage-link-${kind}`}>
      <span className="lineage-badge">{kind === "direct" ? "직접" : "간접"}</span>
      {onSelectNode ? (
        <button className="lineage-link-button" onClick={() => onSelectNode(post.post_id)}>
          {post.post_title}
        </button>
      ) : (
        post.post_title
      )}
    </li>
  );
}

export function EventLineagePanel({
  lineage,
  graph,
  postId,
  onSelectNode,
}: EventLineagePanelProps) {
  return (
    <section className="popup-section" aria-label="사건 lineage">
      <h3 id="post-event-lineage">사건 lineage</h3>
      {!lineage ? <p>Loading lineage...</p> : null}
      {lineage ? (
        <EventLineageBody
          lineage={lineage}
          graph={graph}
          postId={postId}
          onSelectNode={onSelectNode}
        />
      ) : null}
    </section>
  );
}

function EventLineageBody({
  lineage,
  graph,
  postId,
  onSelectNode,
}: {
  lineage: PostLineage;
  graph: LineageGraph | null;
  postId: string;
  onSelectNode?: (postId: string) => void;
}) {
  const scoped = graph ? subgraphForPost(graph, postId) : { nodes: [], edges: [] };
  const hasLinks = lineage.direct.length > 0 || lineage.indirect.length > 0;
  if (scoped.nodes.length === 0 && !hasLinks) {
    return <p className="lineage-empty">{EVENT_LINEAGE_EMPTY}</p>;
  }
  return (
    <>
      {scoped.nodes.length > 0 && onSelectNode ? (
        <LineageDag graph={scoped} onSelectPost={onSelectNode} currentPostId={postId} />
      ) : null}
      {hasLinks ? (
        <ul className="lineage-list">
          {lineage.direct.map((post) => (
            <LineageLink key={post.post_id} post={post} kind="direct" onSelectNode={onSelectNode} />
          ))}
          {lineage.indirect.map((post) => (
            <LineageLink key={post.post_id} post={post} kind="indirect" onSelectNode={onSelectNode} />
          ))}
        </ul>
      ) : null}
    </>
  );
}
