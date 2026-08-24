import { formatLeftoverObservedExpected } from "../leftoverObservedExpected";
import { formatLeftoverMapRank } from "../leftoverMapRank";
import { formatLeftoverMapReconstruction } from "../leftoverMapReconstruction";
import {
  leftoverPairAriaLabel,
  leftoverPairNextAction,
  leftoverPairOpenOptions,
  leftoverPairTitle,
  type LeftoverPairOpen,
  type LeftoverPairOpenOptions,
} from "../leftoverPairGuidance";

export function LeftoverPairButton({
  pair,
  leftoverDistance,
  observedResponse,
  expectedResponse,
  leftoverMapRank,
  leftoverMapReconstruction,
  onOpen,
}: {
  pair: LeftoverPairOpen;
  leftoverDistance: number;
  observedResponse?: number | null;
  expectedResponse?: number | null;
  leftoverMapRank?: number | null;
  leftoverMapReconstruction?: number | null;
  onOpen: (postId: string, options: LeftoverPairOpenOptions) => void;
}) {
  const observedExpected = formatLeftoverObservedExpected(observedResponse, expectedResponse);
  const mapRank = formatLeftoverMapRank(leftoverMapRank);
  const mapReconstruction = formatLeftoverMapReconstruction(leftoverMapReconstruction);
  return (
    <button
      type="button"
      className="post-list-item"
      aria-label={leftoverPairAriaLabel(pair)}
      onClick={() => onOpen(pair.post_id, leftoverPairOpenOptions(pair))}
    >
      <span className="ticket-title">{leftoverPairTitle(pair)}</span>
      <span className="post-badge">{leftoverPairNextAction(pair)}</span>
      {observedExpected ? <span className="post-badge">{observedExpected}</span> : null}
      {mapRank ? <span className="post-badge">{mapRank}</span> : null}
      {mapReconstruction ? <span className="post-badge">{mapReconstruction}</span> : null}
      <span className="post-badge">d {leftoverDistance.toFixed(2)}</span>
    </button>
  );
}
