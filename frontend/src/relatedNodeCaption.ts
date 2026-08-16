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
 * organization identity is known, that organization. A unique org
 * without a side still names the org so a missing side cannot revive
 * the ontology-class caption. Organization chips use the entity-level
 * label. Post chips are the title only. Click the chip to continue
 * the walk, or open the Keyman list when you need every affiliation.
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
      if (side && org) {
        return `${name}, ${org} (${side})`;
      }
      if (side) {
        return `${name} (${side})`;
      }
      if (org) {
        return `${name}, ${org}`;
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
