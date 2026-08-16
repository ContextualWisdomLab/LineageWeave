import type { Meta, StoryObj } from "@storybook/react-vite";
import type { AnalysisRun, AnalysisRunKindCode, AnalysisRunStatusCode } from "../api";
import { AnalysisRunListButton } from "./AnalysisRunListButton";

const KIND_LABEL: Record<AnalysisRunKindCode, string> = {
  analysis_run_lineage: "Lineage reconstruction",
  analysis_run_tepp: "TEPP measurement",
  analysis_run_report: "Period report",
};

const STATUS_LABEL: Record<AnalysisRunStatusCode, string> = {
  analysis_status_pending: "Pending",
  analysis_status_running: "Running",
  analysis_status_succeeded: "Succeeded",
  analysis_status_failed: "Failed",
  analysis_status_cancelled: "Cancelled",
};

function demoRun(
  kind: AnalysisRunKindCode,
  status: AnalysisRunStatusCode,
): AnalysisRun {
  return {
    analysis_run_id: `run-demo-${kind}-${status}`,
    run_kind_code: kind,
    run_kind_label: KIND_LABEL[kind],
    scope_kind_code: "analysis_scope_corporate_entity",
    scope_kind_label: "Corporate entity",
    scope_entity_name: "Demo Corp",
    status_code: status,
    status_label: STATUS_LABEL[status],
    knowledge_cutoff: "2026-01-12T12:00:00Z",
    requested_at: "2026-01-12T12:34:00Z",
    source_counts: [
      {
        count_type_code: "analysis_count_document",
        count_type_label: "Documents",
        count_value: 3,
      },
    ],
  };
}

const meta = {
  title: "AnalysisRuns/AnalysisRunListButton",
  component: AnalysisRunListButton,
  args: {
    run: demoRun("analysis_run_tepp", "analysis_status_pending"),
    onOpen: () => undefined,
  },
} satisfies Meta<typeof AnalysisRunListButton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const PendingTepp: Story = {};

export const RunningTepp: Story = {
  args: { run: demoRun("analysis_run_tepp", "analysis_status_running") },
};

export const FailedTepp: Story = {
  args: { run: demoRun("analysis_run_tepp", "analysis_status_failed") },
};

export const CancelledTepp: Story = {
  args: { run: demoRun("analysis_run_tepp", "analysis_status_cancelled") },
};

export const PendingLineage: Story = {
  args: { run: demoRun("analysis_run_lineage", "analysis_status_pending") },
};

export const FailedLineage: Story = {
  args: { run: demoRun("analysis_run_lineage", "analysis_status_failed") },
};

export const PendingPeriodReport: Story = {
  args: { run: demoRun("analysis_run_report", "analysis_status_pending") },
};

export const FailedPeriodReport: Story = {
  args: { run: demoRun("analysis_run_report", "analysis_status_failed") },
};
