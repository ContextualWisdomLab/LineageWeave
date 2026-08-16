import type { RelatedNode } from "./api";

const NODE_PERSON = "node_person";
const NODE_POST = "node_post";
const NODE_CORPORATE_ENTITY = "node_corporate_entity";

type RelatedNodeKind = typeof NODE_PERSON | typeof NODE_POST | typeof NODE_CORPORATE_ENTITY;

function isRelatedNodeKind(code: string): code is RelatedNodeKind {
  return code === NODE_PERSON || code === NODE_POST || code === NODE_CORPORATE_ENTITY;
}

/**
 * Decision-facing label for a related-node chip.
 *
 * Person chips use the authorized side label and, when exactly one
 * organization identity is known, that organization. A known-plural
 * set uses "multiple organizations" so the next action is to open
 * the Keyman list -- that is not the same as a missing affiliation.
 * A unique org without a side still names the org so a missing side
 * cannot revive the ontology-class caption. Organization chips use
 * the entity-level label. Post chips are the title only.
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
      const context = org || (node.affiliation_ambiguous ? "multiple organizations" : "");
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
