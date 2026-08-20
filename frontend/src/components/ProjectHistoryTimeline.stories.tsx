import type { Meta, StoryObj } from "@storybook/react-vite";
import type { ProjectHistory } from "../api";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";

const completeHistory: ProjectHistory = {
  project_key: "P-1042",
  project_name: "OO Transformer",
  events: [
    ["order", "project_event_order", "Order awarded", "Order awarded", "2022-03-14T09:00:00Z"],
    ["spec", "project_event_spec_change", "Specification changed", "Specification revision approved", "2023-06-01T09:00:00Z"],
    ["delivery", "project_event_delivery", "Delivered", "Delivery completed", "2024-11-18T09:00:00Z"],
    ["voc", "project_event_voc", "VOC received", "Insulation performance VOC", "2026-02-03T09:00:00Z"],
    ["rebid", "project_event_rebid", "Rebid", "Rebid opportunity opened", "2026-08-10T09:00:00Z"],
  ].map(([id, type, label, title, occurred]) => ({
    project_history_event_id: id,
    event_type_code: type,
    event_type_label: label,
    event_title: title,
    occurred_at: occurred,
    ended_at: null,
    evidence_post_id: `post-${id}`,
    evidence_post_title: `${title} source`,
    ontology_iri: `https://contextualwisdomlab.github.io/lineageweave/project-history#${type}`,
    evidence_count: 1,
  })),
  relations: [
    {
      source_project_history_event_id: "delivery",
      target_project_history_event_id: "voc",
      relation_type_code: "project_relation_related_to",
      relation_type_label: "Related to",
      evidence_post_id: "post-voc",
      evidence_post_title: "VOC source",
      relation_confidence: null,
      causal: false,
    },
  ],
  responsibility_assignments: [
    {
      project_responsibility_assignment_id: "sales",
      cataloged_person_id: "person-sales",
      person_name: "Synthetic Sales Owner",
      responsibility_role_code: "project_role_sales",
      responsibility_role_label: "Sales",
      valid_from: "2022-03-01T00:00:00Z",
      valid_to: "2023-05-20T00:00:00Z",
      evidence_post_id: "post-order",
      evidence_post_title: "Order source",
    },
    {
      project_responsibility_assignment_id: "pm",
      cataloged_person_id: "person-pm",
      person_name: "Synthetic Project Manager",
      responsibility_role_code: "project_role_project_manager",
      responsibility_role_label: "Project manager",
      valid_from: "2023-06-01T00:00:00Z",
      valid_to: "2026-01-01T00:00:00Z",
      evidence_post_id: "post-spec",
      evidence_post_title: "Specification source",
    },
    {
      project_responsibility_assignment_id: "service",
      cataloged_person_id: "person-service",
      person_name: "Synthetic Service Owner",
      responsibility_role_code: "project_role_service",
      responsibility_role_label: "Service",
      valid_from: "2026-01-01T00:00:00Z",
      valid_to: null,
      evidence_post_id: "post-voc",
      evidence_post_title: "VOC source",
    },
  ],
  handover_gaps: [
    {
      previous_assignment_id: "sales",
      next_assignment_id: "pm",
      gap_start: "2023-05-20T00:00:00Z",
      gap_end: "2023-06-01T00:00:00Z",
      gap_days: 12,
      gap_basis: "visible_assignment_evidence",
    },
  ],
  truncated: false,
  evidence_boundary: "authorized_source_posts_only",
};

const meta = {
  title: "Buyer/Project history timeline",
  component: ProjectHistoryTimeline,
  parameters: { layout: "padded" },
  args: { history: completeHistory, currentPostId: "post-voc" },
} satisfies Meta<typeof ProjectHistoryTimeline>;

export default meta;
type Story = StoryObj<typeof meta>;

export const CompleteLifecycle: Story = {};

export const NoAssignments: Story = {
  args: { history: { ...completeHistory, responsibility_assignments: [], handover_gaps: [] } },
};

export const SingleAssignment: Story = {
  args: {
    history: {
      ...completeHistory,
      responsibility_assignments: [completeHistory.responsibility_assignments[0]],
      handover_gaps: [],
    },
  },
};

export const HiddenEvidenceRemoved: Story = {
  args: {
    history: {
      ...completeHistory,
      events: completeHistory.events.filter((event) => event.project_history_event_id !== "delivery"),
      relations: [],
    },
  },
};

export const TruncatedHistory: Story = {
  args: { history: { ...completeHistory, truncated: true } },
};

export const EmptyEvidence: Story = {
  args: {
    history: {
      ...completeHistory,
      events: [],
      relations: [],
      responsibility_assignments: [],
      handover_gaps: [],
    },
  },
};
