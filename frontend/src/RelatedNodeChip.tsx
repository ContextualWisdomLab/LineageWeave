import type { RelatedNode } from "./api";
import {
  relatedNodeCaption,
  relatedNodeChipAccessibleName,
  type RelatedNodeChipAction,
} from "./relatedNodeCaption";
import "./relatedNodeTokens.css";

/**
 * One related-node chip. Caption, tokens, and accessible name stay
 * one contract so the walk inventory matches the Figma chip library
 * (ADR 0002 / 0014).
 */
export function RelatedNodeChip({
  node,
  action,
  onSelect,
}: {
  node: RelatedNode;
  action: RelatedNodeChipAction;
  onSelect: (node: RelatedNode) => void;
}) {
  const caption = relatedNodeCaption(node);
  return (
    <button
      type="button"
      className="related-node-chip"
      aria-label={relatedNodeChipAccessibleName(caption, action)}
      onClick={() => onSelect(node)}
    >
      {caption}
    </button>
  );
}
