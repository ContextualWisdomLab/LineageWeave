import type { RelatedNode } from "./api";
import { t, tf } from "./i18n";

const NODE_PERSON = "node_person";
const NODE_POST = "node_post";
const NODE_CORPORATE_ENTITY = "node_corporate_entity";
const NODE_TEAM = "node_team";

type RelatedNodeKind =
  | typeof NODE_PERSON
  | typeof NODE_POST
  | typeof NODE_CORPORATE_ENTITY
  | typeof NODE_TEAM;

function isRelatedNodeKind(code: string): code is RelatedNodeKind {
  return (
    code === NODE_PERSON ||
    code === NODE_POST ||
    code === NODE_CORPORATE_ENTITY ||
    code === NODE_TEAM
  );
}

/**
 * Decision-facing label for a related-node chip.
 *
 * Person chips use the authorized side label and, when exactly one
 * organization identity is known, that organization. A known-plural
 * set uses "multiple organizations" even if a name is also present
 * so a stale payload cannot invent a primary. That is not the same
 * as a missing affiliation.
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
      const context = node.affiliation_ambiguous ? t("multiple organizations") : org || "";
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
    case NODE_TEAM:
      return name;
    default: {
      const _exhaustive: never = kind;
      return _exhaustive;
    }
  }
}

export type RelatedNodeChipAction = "walk_person" | "walk_entity" | "walk_team" | "open_post";

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
    case "walk_team":
      return tf("Related nodes for {name}", { name: caption });
    case "open_post":
      return tf("Open related post: {label}", { label: caption });
    default: {
      const _exhaustive: never = action;
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
    return t(
      "Multiple organizations are recorded. Read every organization in the Keyman list above, then continue the walk.",
    );
  }
  return t(
    "Multiple organizations are recorded. Extract Keymen to list every organization, then continue the walk.",
  );
}
