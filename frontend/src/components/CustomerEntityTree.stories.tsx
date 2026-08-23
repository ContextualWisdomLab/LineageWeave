import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { CustomerEntityTreeRow, type CustomerEntityTreeNode } from "./CustomerEntityTree";
import "../App.css";

const LEAF_ENTITY = {
  corporate_entity_id: "entity-plant",
  entity_name: "삼성전자 광주공장",
  corporate_entity_code: "SEC-GWANGJU",
  entity_level_code: "plant",
  entity_level_label: "Plant",
  parent_entity_id: "entity-hq",
  scope_facets: ["authorized_granted" as const],
};

const HQ_ENTITY = {
  corporate_entity_id: "entity-hq",
  entity_name: "삼성전자 본사",
  corporate_entity_code: "SEC-HQ",
  entity_level_code: "company",
  entity_level_label: "Company",
  parent_entity_id: "entity-korea",
  scope_facets: ["authorized_granted" as const],
};

const KOREA_ENTITY = {
  corporate_entity_id: "entity-korea",
  entity_name: "삼성전자 한국",
  corporate_entity_code: "SEC-KR",
  entity_level_code: "group",
  entity_level_label: "Group",
  parent_entity_id: null,
  scope_facets: ["authorized_own" as const, "observed_hierarchy" as const],
};

// Mirrors the "삼성 - 삼성전자 한국 - 삼성전자 본사 - 삼성전자 광주공장" chain
// named in the product ask for the affiliate-hierarchy tree (issue #4).
const HIERARCHY_NODE: CustomerEntityTreeNode = {
  entity: KOREA_ENTITY,
  children: [
    {
      entity: HQ_ENTITY,
      children: [{ entity: LEAF_ENTITY, children: [] }],
    },
  ],
};

const meta = {
  title: "CustomerMaster/CustomerEntityTreeRow",
  component: CustomerEntityTreeRow,
  args: {
    node: HIERARCHY_NODE,
    depth: 0,
    expandedEntityId: null,
    relatedByEntity: {},
    relatedLoading: null,
    onToggle: () => undefined,
    onOpenPost: () => undefined,
  },
} satisfies Meta<typeof CustomerEntityTreeRow>;

export default meta;

type Story = StoryObj<typeof meta>;

// Renders the full nested chain collapsed -- the visual proof that
// corporate_entity.parent_entity_id now produces a real affiliate tree
// instead of a flat list (issue #4's "통합 고객사 계열 tree AI").
export const Collapsed: Story = {};

export const ExpandedWithRelatedPosts: Story = {
  args: {
    expandedEntityId: "entity-korea",
    relatedByEntity: {
      "entity-korea": [
        {
          node_id: "post-1",
          node_type_code: "node_post",
          relevance: 1,
          label: "2026년 1분기 공급망 현황 보고",
          post_body_excerpt: "이번 분기 반도체 공급망 안정화를 위한 협력 방안을 논의했습니다.",
          post_body_truncated: true,
        },
      ],
    },
  },
};

export const RelatedPostsLoading: Story = {
  args: {
    expandedEntityId: "entity-korea",
    relatedLoading: "entity-korea",
  },
};

export const ExpandedWithNoRelatedPosts: Story = {
  args: {
    expandedEntityId: "entity-korea",
    relatedByEntity: { "entity-korea": [] },
  },
};

// Demonstrates the actual fix for issues #1/#3: clicking a related post
// invokes onOpenPost in place instead of navigating away. This story is
// interactive -- open it in Storybook and click "Open related post" to
// see the callback fire without any route change.
export const OpeningARelatedPostInPlace: Story = {
  render: function InteractiveDemo(args) {
    const [openedPostId, setOpenedPostId] = useState<string | null>(null);
    return (
      <div>
        <ul className="customer-master-list customer-master-tree">
          <CustomerEntityTreeRow
            {...args}
            expandedEntityId="entity-korea"
            relatedByEntity={{
              "entity-korea": [
                {
                  node_id: "post-1",
                  node_type_code: "node_post",
                  relevance: 1,
                  label: "2026년 1분기 공급망 현황 보고",
                },
              ],
            }}
            onOpenPost={setOpenedPostId}
          />
        </ul>
        <p role="status">
          {openedPostId ? `Opened in place: ${openedPostId} (no navigation occurred)` : "No post opened yet."}
        </p>
      </div>
    );
  },
};
