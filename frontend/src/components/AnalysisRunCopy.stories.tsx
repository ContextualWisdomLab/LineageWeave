import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import type { AnalysisRun } from "../api";
import { analysisRunCaption, analysisRunCorpusHint, periodGroupMeasureCaption } from "../analysisRunCopy";
import "../App.css";

function AnalysisRunCopyPreview({
  kind,
  status,
}: {
  kind: AnalysisRun["run_kind_code"];
  status: AnalysisRun["status_code"];
}) {
  const run = {
    run_kind_code: kind,
    status_code: status,
    status_label: status === "analysis_status_failed" ? "Failed" : "Pending",
    scope_kind_label: "Demo workspace",
  } as AnalysisRun;
  return (
    <section className="popup-section" aria-label="Analysis run detail">
      <h3>{analysisRunCaption(run)}</h3>
      <p className="post-meta">{analysisRunCorpusHint(run)}</p>
    </section>
  );
}

const meta = {
  title: "Analysis/RunCopy",
  component: AnalysisRunCopyPreview,
  parameters: { layout: "padded" },
} satisfies Meta<typeof AnalysisRunCopyPreview>;

export default meta;
type Story = StoryObj<typeof meta>;

export const FailedMeasurement: Story = {
  args: { kind: "analysis_run_tepp", status: "analysis_status_failed" },
  play: async ({ canvasElement }) => {
    const detail = within(canvasElement).getByRole("region", { name: "Analysis run detail" });
    await expect(detail).toHaveTextContent("Record measurement · Failed");
    await expect(detail).toHaveTextContent("Ask an administrator to restore analysis");
    await expect(detail).not.toHaveTextContent(/TEPP|transport|provider|model|worker/i);
  },
};

export const PendingTopicHistory: Story = {
  args: { kind: "analysis_run_topic_lineage", status: "analysis_status_pending" },
  play: async ({ canvasElement }) => {
    const detail = within(canvasElement).getByRole("region", { name: "Analysis run detail" });
    await expect(detail).toHaveTextContent("Topic history · Pending");
    await expect(detail).toHaveTextContent("Start this run to request a result");
  },
};

export const PeriodGroupNeedsReview: Story = {
  args: { kind: "analysis_run_report", status: "analysis_status_succeeded" },
  render: () => (
    <section className="popup-section" aria-label="Period group summary">
      <span className="ticket-title">{periodGroupMeasureCaption({
        grouping_key: "demo-group",
        grouping_label: "Demo group",
        mean_theta: 0.42,
        fit_converged: false,
      })}</span>
    </section>
  ),
  play: async ({ canvasElement }) => {
    const summary = within(canvasElement).getByRole("region", { name: "Period group summary" });
    await expect(summary).toHaveTextContent("Ask an administrator to review this report before using it.");
    await expect(summary).not.toHaveTextContent(/grm|model|worker|provider|transport/i);
  },
};
