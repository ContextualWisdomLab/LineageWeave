import type { LineageGraph, PostLineage, UnverifiedCandidate } from "../api";
import { EventLineagePanel } from "./EventLineagePanel";
import { GroundedQa, type GroundedQaAnswer } from "./GroundedQa";

export type AskCubeeProps = {
  postId: string | null;
  postTitle?: string | null;
  lineage: PostLineage | null;
  graph: LineageGraph | null;
  onAsk: (question: string) => Promise<GroundedQaAnswer>;
  onSelectNode?: (postId: string) => void;
  onPromoteCandidate?: (candidate: UnverifiedCandidate) => void;
};

export function AskCubee({
  postId,
  postTitle,
  lineage,
  graph,
  onAsk,
  onSelectNode,
  onPromoteCandidate,
}: AskCubeeProps) {
  return (
    <section className="popup-section lineage-home" aria-label="Ask Agent">
      <h2>Ask Agent</h2>
      {postTitle ? <p className="post-meta">Event · {postTitle}</p> : null}
      {postId && lineage ? (
        <EventLineagePanel lineage={lineage} graph={graph} postId={postId} onSelectNode={onSelectNode} />
      ) : null}
      <GroundedQa heading="Ask Agent" onAsk={onAsk} onPromoteCandidate={onPromoteCandidate} />
    </section>
  );
}
