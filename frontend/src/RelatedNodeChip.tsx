import type { RelatedNode } from "./api";
import { NODE_CORPORATE_ENTITY, NODE_PERSON, NODE_POST } from "./nodeTypes";
import { relatedNodeAriaLabel, relatedNodeCaption } from "./relatedNodeCaption";

function isWalkChip(node: RelatedNode): boolean {
  return (
    node.node_type_code === NODE_PERSON ||
    node.node_type_code === NODE_CORPORATE_ENTITY ||
    node.node_type_code === NODE_POST
  );
}

/**
 * Compact related-node control used in the Keyman walk.
 *
 * Click a person or organization chip to continue the walk. Click a
 * post chip to open that source. When the caption says
 * "multiple organizations", open the Keyman list for every affiliation.
 */
export function RelatedNodeChip({
  node,
  onSelect,
}: {
  node: RelatedNode;
  onSelect: (node: RelatedNode) => void;
}) {
  const caption = relatedNodeCaption(node);
  if (!isWalkChip(node)) {
    return <span className="related-node-chip related-node-chip-static">{caption}</span>;
  }
  return (
    <button
      type="button"
      className="keyman-select related-node-chip"
      aria-label={relatedNodeAriaLabel(node, caption)}
      onClick={() => onSelect(node)}
    >
      {caption}
    </button>
  );
}
