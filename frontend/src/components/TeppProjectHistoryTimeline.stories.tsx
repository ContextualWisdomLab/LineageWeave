import type { Meta, StoryObj } from "@storybook/react";

import { TeppProjectHistoryTimeline } from "./TeppProjectHistoryTimeline";

const meta = {
  title: "Analysis/TEPP Project History Timeline",
  component: TeppProjectHistoryTimeline,
  args: {
    onOpenPost: () => undefined,
    history: {
      contract_version: 1,
      project_key: "project-alpha",
      project_name: "Project Alpha",
      focus_event_id: "event-voc",
      knowledge_cutoff: "2026-08-19T00:00:00Z",
      inference_status: "temporal_association_only",
      participant_count: 3,
      history_span_start: "2022-03-01T00:00:00Z",
      history_span_end: "2026-08-01T00:00:00Z",
      events: [
        {
          event_id: "event-contract",
          event_type_code: "contract_awarded",
          event_title: "Project Alpha contract awarded",
          occurred_at: "2022-03-01T00:00:00Z",
          available_at: "2022-03-01T00:00:00Z",
          source_post_id: "post-contract",
          evidence_text: "The order was awarded.",
          actor_ids: ["actor-sales"],
        },
        {
          event_id: "event-spec",
          event_type_code: "specification_changed",
          event_title: "Customer specification changed",
          occurred_at: "2023-06-01T00:00:00Z",
          available_at: "2023-06-01T00:00:00Z",
          source_post_id: "post-spec",
          evidence_text: "The specification changed.",
          actor_ids: ["actor-engineering"],
        },
        {
          event_id: "event-delivery",
          event_type_code: "delivered",
          event_title: "Initial delivery completed",
          occurred_at: "2024-01-01T00:00:00Z",
          available_at: "2024-01-01T00:00:00Z",
          source_post_id: "post-delivery",
          evidence_text: "The first delivery was completed.",
          actor_ids: ["actor-operations"],
        },
        {
          event_id: "event-voc",
          event_type_code: "voc_received",
          event_title: "Customer VOC registered",
          occurred_at: "2026-06-01T00:00:00Z",
          available_at: "2026-06-01T00:00:00Z",
          source_post_id: "post-voc",
          evidence_text: "A customer VOC was registered.",
          actor_ids: ["actor-sales", "actor-operations", "actor-customer"],
        },
        {
          event_id: "event-rebid",
          event_type_code: "rebid_started",
          event_title: "Rebid preparation started",
          occurred_at: "2026-08-01T00:00:00Z",
          available_at: "2026-08-01T00:00:00Z",
          source_post_id: "post-rebid",
          evidence_text: "Rebid preparation started.",
          actor_ids: ["actor-sales"],
        },
      ],
      findings: [
        {
          finding_code: "specification_change_before_focus",
          summary:
            "An explicit specification-change event precedes the focus event. This is a temporal association, not a causal conclusion.",
          related_event_ids: ["event-spec", "event-voc"],
          evidence_post_ids: ["post-spec", "post-voc"],
        },
      ],
    },
  },
} satisfies Meta<typeof TeppProjectHistoryTimeline>;

export default meta;
type Story = StoryObj<typeof meta>;

export const MinimumBuyerRequirement: Story = {};
