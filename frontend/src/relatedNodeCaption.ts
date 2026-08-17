import type { RelatedNode } from "./api";

export const NODE_PERSON = "node_person";
export const NODE_POST = "node_post";
export const NODE_CORPORATE_ENTITY = "node_corporate_entity";

/**
 * Decision-facing label for a related-node chip on the #92 walk.
 *
 * Person chips use the authorized side label and, when exactly one
 * organization identity is known, that organization. Multiple
 * distinct affiliations stay omitted so a second org is never
 * collapsed into an invented primary. Organization chips use the
 * entity-level label. Post chips are the title only.
 */
export function relatedNodeCaption(node: RelatedNode): string {
  const name = node.label ?? node.node_id;
  if (node.node_type_code === NODE_PERSON) {
    const side = node.person_side_label?.trim() || node.person_side_code?.trim();
    const org = node.affiliation_organization_name?.trim();
    if (side && org) {
      return `${name}, ${org} (${side})`;
    }
    if (side) {
      return `${name} (${side})`;
    }
  }
  if (node.node_type_code === NODE_CORPORATE_ENTITY) {
    const level = node.entity_level_label?.trim() || node.entity_level_code?.trim();
    if (level) {
      return `${name} (${level})`;
    }
  }
  if (node.node_type_code === NODE_POST) {
    return name;
  }
  return `${name} (${node.ontology_label ?? node.node_type_code})`;
}

export type RelatedNodeChipAction = "walk_person" | "walk_entity" | "open_post";

/**
 * Accessible name for a related-node chip.
 *
 * The visible caption is contained in the name (WCAG 2.2 Success
 * Criterion 2.5.3). Walk chips continue the graph. Post chips open
 * the evidence body.
 */
export function relatedNodeChipAccessibleName(
  caption: string,
  action: RelatedNodeChipAction,
): string {
  switch (action) {
    case "walk_person":
    case "walk_entity":
      return `Related nodes for ${caption}`;
    case "open_post":
      return `Open related post: ${caption}`;
    default: {
      const _exhaustive: never = action;
      return _exhaustive;
    }
  }
}
