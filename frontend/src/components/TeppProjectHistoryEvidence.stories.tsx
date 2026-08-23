import type { Meta, StoryObj } from "@storybook/react";

import { TeppProjectHistoryEvidence } from "./TeppProjectHistoryEvidence";

const meta = {
  title: "Buyer/TEPP Project History Evidence",
  component: TeppProjectHistoryEvidence,
  args: {
    validation: {
      status: "validated",
      next_action_code: "open_source_evidence",
      project_history: {
        contract_version: 1,
        project_key: "P-100",
        project_name: "Synthetic transformer renewal",
        focus_event_id: "voc",
        knowledge_cutoff: "2026-08-20T12:00:00Z",
        history_span_start: "2022-03-11T09:00:00Z",
        history_span_end: "2026-02-02T09:00:00Z",
        participant_count: 2,
        inference_status: "temporal_association_only",
        event_count: 3,
        findings: [
          {
            finding_code: "specification_change_before_focus",
            summary: "An explicit specification-change event precedes the focus event.",
            related_event_ids: ["spec"],
            evidence_post_ids: ["post-spec"],
          },
        ],
      },
    },
    sourceLabels: { "post-spec": "Synthetic specification changed" },
    onOpenPost: () => undefined,
  },
} satisfies Meta<typeof TeppProjectHistoryEvidence>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Validated: Story = {};

export const NotConfigured: Story = {
  args: {
    validation: {
      status: "not_configured",
      project_history: null,
      next_action_code: "configure_tepp_project_history",
    },
  },
};

export const ServiceUnavailable: Story = {
  args: {
    validation: {
      status: "unavailable",
      project_history: null,
      next_action_code: "retry_tepp_project_history",
    },
  },
};
