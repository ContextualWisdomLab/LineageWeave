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
  onOpen,
}: {
  pair: LeftoverPairOpen;
  leftoverDistance: number;
  onOpen: (postId: string, options: LeftoverPairOpenOptions) => void;
}) {
  return (
    <button
      type="button"
      className="post-list-item"
      aria-label={leftoverPairAriaLabel(pair)}
      onClick={() => onOpen(pair.post_id, leftoverPairOpenOptions(pair))}
    >
      <span className="ticket-title">{leftoverPairTitle(pair)}</span>
      <span className="post-badge">{leftoverPairNextAction(pair)}</span>
      <span className="post-badge">d {leftoverDistance.toFixed(2)}</span>
    </button>
  );
}
