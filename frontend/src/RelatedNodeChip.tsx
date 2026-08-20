import type { RelatedNode } from "./api";
import {
  relatedNodeCaption,
  relatedNodeChipAccessibleName,
  type RelatedNodeChipAction,
} from "./relatedNodeCaption";

/**
 * One related-node chip. Use this module for every repeating walk
 * control so caption, tokens, and accessible name stay one contract.
 */
export function RelatedNodeChip({
    node,
    action,
    current,
    onSelect,
  }: {
    node: RelatedNode;
    action: RelatedNodeChipAction;
    current?: boolean;
    onSelect: (node: RelatedNode) => void;
  }) {
  const caption = relatedNodeCaption(node);
  return (
    <button
      type="button"
      className="related-node-chip"
      aria-label={relatedNodeChipAccessibleName(caption, action)}
      aria-current={current ? "true" : undefined}
      onClick={() => onSelect(node)}
    >
      {caption}
    </button>
  );
}
