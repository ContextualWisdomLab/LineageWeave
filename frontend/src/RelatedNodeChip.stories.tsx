import type { RelatedNode } from "./api";
import { RelatedNodeChip } from "./RelatedNodeChip";

/**
 * Storybook inventory for the repeating related-node chip.
 *
 * Host this file with Storybook 10 (Vite + React) when the later
 * analysis-run token stack lands. Until then the same four states
 * are locked by RelatedNodeChip.test.tsx and relatedNodeCaption.test.ts.
 */
const meta = {
  title: "Lineage/RelatedNodeChip",
  component: RelatedNodeChip,
};

export default meta;

function node(partial: Partial<RelatedNode> & Pick<RelatedNode, "node_type_code">): RelatedNode {
  return {
    node_id: "node-1",
    relevance: 0.4,
    ...partial,
  };
}

export const UniqueAffiliation = {
  args: {
    action: "walk_person",
    onSelect: () => undefined,
    node: node({
      node_type_code: "node_person",
      label: "Ada West",
      person_side_label: "Our side",
      affiliation_organization_name: "Demo Corp",
    }),
  },
};

export const PluralAffiliations = {
  args: {
    action: "walk_person",
    onSelect: () => undefined,
    node: node({
      node_type_code: "node_person",
      label: "Priya Nair",
      person_side_label: "Counterparty",
      affiliation_ambiguous: true,
    }),
  },
};

export const MissingAffiliation = {
  args: {
    action: "walk_person",
    onSelect: () => undefined,
    node: node({
      node_type_code: "node_person",
      label: "Priya Nair",
      person_side_label: "Counterparty",
    }),
  },
};

export const OrganizationAndPost = {
  render: () => (
    <ul>
      <li>
        <RelatedNodeChip
          action="walk_entity"
          onSelect={() => undefined}
          node={node({
            node_type_code: "node_corporate_entity",
            label: "Demo Corp",
            entity_level_label: "Company",
          })}
        />
      </li>
      <li>
        <RelatedNodeChip
          action="open_post"
          onSelect={() => undefined}
          node={node({
            node_type_code: "node_post",
            label: "Linked post",
          })}
        />
      </li>
    </ul>
  ),
};
