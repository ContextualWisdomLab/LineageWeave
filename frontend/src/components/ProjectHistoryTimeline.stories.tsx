import type { Meta, StoryObj } from "@storybook/react";

import type { ProjectHistoryProjection, ProjectHistoryTruthStatus } from "../projectHistory";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";

const event = (
  eventId: string,
  title: string,
  type: string,
  occurredAt: string,
  transition: "continuous" | "handoff" | "assignment_gap" | null,
  actorName?: string,
  truthStatus: ProjectHistoryTruthStatus = "observed",
) => {
  const responsibilityEvidence = actorName
    ? [
        {
          actor_key: `actor:${actorName}`,
          actor_name: actorName,
          actor_type_code: "prov_person",
          affiliated_organization_name: "Demo Corp",
          responsibility:
            truthStatus === "observed" ? "Source author" : `Coordinate ${title.toLowerCase()}`,
          truth_status_code: truthStatus,
          provenance:
            truthStatus === "observed" ? "source_post.source_author" : "post_summary_role",
        },
      ]
    : [];
  return {
    event_id: eventId,
    source_post_id: `post-${eventId}`,
    event_title: title,
    event_type_code: type,
    event_type_basis_code: "display_classification" as const,
    occurred_at: occurredAt,
    time_basis_code: "document_time" as const,
    voc_type_code: eventId === "voc" ? "voc" : "vom",
    source_stage_code: null,
    source_detail_state_code: null,
    project_matches: [],
    responsibility_evidence: responsibilityEvidence,
    observed_responsibilities: responsibilityEvidence.filter(
      (row) => row.truth_status_code === "observed",
    ),
    responsibility_transition_code: transition,
    responsibility_transition_truth_status_code:
      transition === null ? null : truthStatus,
    related_prior_paths: [],
  };
};

const projection: ProjectHistoryProjection = {
  contract_version: 1,
  project_key: "P-100",
  normalized_project_key: "p-100",
  project_name: "Northridge renewal",
  focus_event_id: "voc",
  time_basis_code: "document_time",
  knowledge_cutoff: "2026-08-20T00:00:00Z",
  evidence_boundary_code: "authorized_visible_source_posts",
  event_count: 5,
  distinct_actor_count: 3,
  distinct_observed_actor_count: 2,
  truncated: false,
  events: [
    event("award", "Contract awarded", "contract_awarded", "2022-03-11T09:00:00Z", null, "Ada West"),
    event(
      "spec",
      "Specification revision requested",
      "specification_changed",
      "2023-06-15T09:00:00Z",
      "continuous",
      "Ada West",
    ),
    event(
      "delivery",
      "Delivery confirmed",
      "delivered",
      "2024-02-20T09:00:00Z",
      "handoff",
      "Priya Nair",
      "inferred",
    ),
    event("voc", "VOC received", "voc_received", "2026-07-30T09:00:00Z", "assignment_gap"),
    event(
      "rebid",
      "Rebid started",
      "rebid_started",
      "2026-08-10T09:00:00Z",
      "assignment_gap",
      "Bid team",
      "inferred",
    ),
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

export const TruncatedAtSelectedVoc: Story = {
  args: {
    projection: {
      ...projection,
      truncated: true,
    },
  },
};

export const ResponsibilityEvidenceGap: Story = {
  args: {
    projection: {
      ...projection,
      focus_event_id: "voc",
      events: projection.events.map((row) =>
        row.event_id === "voc"
          ? { ...row, responsibility_evidence: [], observed_responsibilities: [] }
          : row,
      ),
    },
  },
};
