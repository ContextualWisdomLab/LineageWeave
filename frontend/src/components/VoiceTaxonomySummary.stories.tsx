import type { Meta, StoryObj } from "@storybook/react";
import { VoiceTaxonomySummary } from "./VoiceTaxonomySummary";

const meta = { title: "Dashboard/VoiceTaxonomySummary", component: VoiceTaxonomySummary } satisfies Meta<typeof VoiceTaxonomySummary>;
export default meta;
type Story = StoryObj<typeof meta>;

export const OverlappingEvidence: Story = { args: { data: {
  total_eligible: 12, classified_unique: 5, multi_membership: 2,
  source_count: 6, derived_count: 7, unavailable: 3, disagreement: 1,
  counts_overlap: true, next_action_text: "Review evidence.",
  category_memberships: [
    { voice_concept_code: "voc", post_count: 5, eligible_percentage: 41.7 },
    { voice_concept_code: "vom", post_count: 4, eligible_percentage: 33.3 },
  ],
} } };
