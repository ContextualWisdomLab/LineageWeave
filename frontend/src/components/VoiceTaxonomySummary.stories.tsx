import type { Meta, StoryObj } from "@storybook/react";
import { setLocale } from "../i18n";
import { VoiceTaxonomySummary } from "./VoiceTaxonomySummary";

const meta = { title: "Dashboard/VoiceTaxonomySummary", component: VoiceTaxonomySummary } satisfies Meta<typeof VoiceTaxonomySummary>;
export default meta;
type Story = StoryObj<typeof meta>;

export const OverlappingEvidence: Story = { args: { data: {
  total_eligible: 12, classified_unique: 5, multi_membership: 2,
  source_count: 6, derived_count: 7, unavailable: 3, disagreement: 1,
  counts_overlap: true,
  category_memberships: [
    { voice_concept_code: "voc", post_count: 5, eligible_percentage: 41.7 },
    { voice_concept_code: "vom", post_count: 4, eligible_percentage: 33.3 },
    { voice_concept_code: "vos", post_count: 2, eligible_percentage: 16.7 },
    { voice_concept_code: "voe", post_count: 1, eligible_percentage: 8.3 },
  ],
} } };

export const KoreanMobile: Story = {
  ...OverlappingEvidence,
  beforeEach: () => {
    setLocale("ko");
    return () => setLocale("en");
  },
  globals: { viewport: { value: "mobile1", isRotated: false } },
};
