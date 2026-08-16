import type { RelatedNode } from "./api";
import {
  NODE_CORPORATE_ENTITY,
  NODE_PERSON,
  NODE_POST,
  isRelatedNodeKind,
} from "./nodeTypes";

/**
 * Decision-facing label for a related-node chip.
 *
 * Person chips use the authorized side label and, when exactly one
 * organization identity is known, that organization. A known-plural
 * set uses "multiple organizations" even if a name is also present
 * so a stale payload cannot invent a primary. That is not the same
 * as a missing affiliation. A unique org without a side still names
 * the org so a missing side cannot revive the ontology-class caption.
 * Organization chips use the entity-level label. Post chips are the
 * title only.
 */
export function relatedNodeCaption(node: RelatedNode): string {
  const name = node.label?.trim() || node.node_id;
  const kind = node.node_type_code;
  if (!isRelatedNodeKind(kind)) {
    return `${name} (${node.ontology_label ?? kind})`;
  }
  switch (kind) {
    case NODE_PERSON: {
      const side = node.person_side_label?.trim() || node.person_side_code?.trim();
      const org = node.affiliation_organization_name?.trim();
      const context = node.affiliation_ambiguous
        ? "multiple organizations"
        : org || "";
      if (side && context) {
        return `${name}, ${context} (${side})`;
      }
      if (side) {
        return `${name} (${side})`;
      }
      if (context) {
        return `${name}, ${context}`;
      }
      return `${name} (${node.ontology_label ?? kind})`;
    }
    case NODE_CORPORATE_ENTITY: {
      const level = node.entity_level_label?.trim() || node.entity_level_code?.trim();
      if (level) {
        return `${name} (${level})`;
      }
      return `${name} (${node.ontology_label ?? kind})`;
    }
    case NODE_POST:
      return name;
    default: {
      const _exhaustive: never = kind;
      return _exhaustive;
    }
  }
}

/**
 * Next action when a related-node chip marks a known-plural affiliation
 * set. The Keyman list is the full N:N surface; the chip click continues
 * the walk and must not be mistaken for "this person has no organization."
 */
export function relatedAffiliationNextAction(hasKeymanList: boolean): string {
  if (hasKeymanList) {
    return (
      "A chip that says multiple organizations is not a missing affiliation. " +
      "Read every organization in the Keyman list above, then click the chip " +
      "to continue the walk."
    );
  }
  return (
    "A chip that says multiple organizations is not a missing affiliation. " +
    "Extract Keymen to list every organization, then click the chip to " +
    "continue the walk."
  );
}

/** Accessible name that contains the visible caption (WCAG 2.5.3). */
export function relatedNodeAriaLabel(node: RelatedNode, caption: string): string {
  if (node.node_type_code === NODE_POST) {
    return `Open related post: ${caption}`;
  }
  return `Related nodes for ${caption}`;
}
