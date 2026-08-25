import type { Meta, StoryObj } from "@storybook/react";

import type { ProjectHistoryProjection } from "../projectHistory";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";

const event = (
  eventId: string,
  title: string,
  occurredAt: string,
  transition: "continuous" | "handoff" | "assignment_gap" | null,
  actorName?: string,
) => ({
  event_id: eventId,
  source_post_id: `post-${eventId}`,
  event_title: title,
  event_type_code: eventId === "voc" ? "voc_received" : "source_recorded",
  event_type_basis_code: "controlled_source_code" as const,
  occurred_at: occurredAt,
  time_basis_code: "document_time" as const,
  voc_type_code: eventId === "voc" ? "voc" : null,
  source_stage_code: null,
  source_detail_state_code: null,
  project_matches: [],
  observed_responsibilities: actorName
    ? [
        {
          actor_key: `actor:${actorName}`,
          actor_name: actorName,
          actor_type_code: "prov_person",
          affiliated_organization_name: "Demo Corp",
          responsibility: `Own ${title.toLowerCase()}`,
          truth_status_code: "observed" as const,
          provenance: "post_summary_role" as const,
        },
      ]
    : [],
  responsibility_transition_code: transition,
  related_prior_paths: [],
});

const projection: ProjectHistoryProjection = {
  contract_version: 1,
  project_key: "P-100",
  normalized_project_key: "p-100",
  project_name: "Northridge renewal",
  focus_event_id: "voc",
  time_basis_code: "document_time",
  event_count: 5,
  distinct_observed_actor_count: 3,
  truncated: false,
  events: [
    event("award", "Contract awarded", "2022-03-11T09:00:00Z", null, "Ada West"),
    event(
      "spec",
      "Specification revision requested",
      "2023-06-15T09:00:00Z",
      "continuous",
      "Ada West",
    ),
    event("delivery", "Delivery confirmed", "2024-02-20T09:00:00Z", "handoff", "Priya Nair"),
    event("voc", "VOC received", "2026-07-30T09:00:00Z", "assignment_gap"),
    event("rebid", "Rebid started", "2026-08-10T09:00:00Z", "assignment_gap", "Bid team"),
  ],
};

projection.events[3].related_prior_paths = [
  {
    source_event_id: "award",
    target_event_id: "voc",
    event_ids: ["award", "spec", "delivery", "voc"],
    edges: [
      { parent_event_id: "award", child_event_id: "spec", fused_score: 0.91 },
      { parent_event_id: "spec", child_event_id: "delivery", fused_score: 0.82 },
      { parent_event_id: "delivery", child_event_id: "voc", fused_score: 0.73 },
    ],
    minimum_fused_score: 0.73,
    truth_status_code: "inferred",
    source_relation_code: "post_lineage_edge",
    provenance: "post_lineage_edge.fused_score",
  },
];

const meta = {
  title: "Buyer/Project History Timeline",
  component: ProjectHistoryTimeline,
  args: {
    projection,
    onOpenPost: () => undefined,
  },
} satisfies Meta<typeof ProjectHistoryTimeline>;

export default meta;
type Story = StoryObj<typeof meta>;

export const AwardToRebid: Story = {};
