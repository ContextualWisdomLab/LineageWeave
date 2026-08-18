import type { LineageGraph, PostLineage } from "../api";
import { EventLineagePanel } from "./EventLineagePanel";
import { GroundedQa, type GroundedQaAnswer } from "./GroundedQa";

export type AskCubeeProps = {
  postId: string | null;
  postTitle?: string | null;
  lineage: PostLineage | null;
  graph: LineageGraph | null;
  onAsk: (question: string) => Promise<GroundedQaAnswer>;
  onSelectNode?: (postId: string) => void;
};

export function AskCubee({ postId, postTitle, lineage, graph, onAsk, onSelectNode }: AskCubeeProps) {
  return (
    <section className="popup-section lineage-home" aria-label="Ask Cubee">
      <h2>Ask Cubee</h2>
      {postTitle ? <p className="post-meta">Event · {postTitle}</p> : null}
      {postId && lineage ? (
        <EventLineagePanel lineage={lineage} graph={graph} postId={postId} onSelectNode={onSelectNode} />
      ) : null}
      <GroundedQa heading="Ask Cubee" onAsk={onAsk} />
    </section>
  );
}
