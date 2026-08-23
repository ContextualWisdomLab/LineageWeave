import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import type { AnalysisRun } from "../api";
import { AnalysisRunNextAction } from "./AnalysisRunNextAction";
import { CutoffKnownBody } from "./CutoffKnownBody";
import "../App.css";

function run(
  partial: Pick<AnalysisRun, "run_kind_code" | "status_code"> & Partial<AnalysisRun>,
): AnalysisRun {
  return {
    analysis_run_id: "run-demo",
    run_kind_label:
      partial.run_kind_code === "analysis_run_tepp"
        ? "TEPP measurement"
        : partial.run_kind_code === "analysis_run_report"
          ? "Period report"
          : "Lineage reconstruction",
    scope_kind_code: "analysis_scope_corporate_entity",
    scope_kind_label: "Corporate entity",
    scope_entity_name: "Demo Corp",
    scope_key: "2026-W02",
    status_label:
      partial.status_code === "analysis_status_failed"
        ? "Failed"
        : partial.status_code === "analysis_status_pending"
          ? "Pending"
          : partial.status_code === "analysis_status_running"
            ? "Running"
            : "Succeeded",
    knowledge_cutoff: "2026-01-12T12:00:00Z",
    requested_at: "2026-01-12T12:31:00Z",
    source_counts: [],
    ...partial,
  };
}

const meta = {
  title: "AnalysisRun/NextAction",
  component: AnalysisRunNextAction,
  parameters: { layout: "padded" },
  args: {
    run: run({ run_kind_code: "analysis_run_lineage", status_code: "analysis_status_failed" }),
    onStart: () => undefined,
    onRefresh: () => undefined,
  },
} satisfies Meta<typeof AnalysisRunNextAction>;

export default meta;

type Story = StoryObj<typeof meta>;

export const FailedLineage: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const status = canvas.getByRole("status");
    await expect(status).toHaveTextContent(/retry reconstruction/i);
    await expect(status).not.toHaveTextContent(/TEPP|measurement service|calibrated/i);
    await expect(canvas.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
    await expect(canvas.queryByRole("button", { name: "Start TEPP measurement" })).not.toBeInTheDocument();
  },
};

export const FailedTepp: Story = {
  args: {
    run: run({ run_kind_code: "analysis_run_tepp", status_code: "analysis_status_failed" }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("status")).toHaveTextContent(/measurement service/i);
    await expect(canvas.getByRole("status")).not.toHaveTextContent(/reconstruction/i);
    await expect(canvas.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
  },
};

export const FailedReport: Story = {
  args: {
    run: run({ run_kind_code: "analysis_run_report", status_code: "analysis_status_failed" }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("status")).toHaveTextContent(/rebuild the period report/i);
    await expect(canvas.getByRole("status")).not.toHaveTextContent(/TEPP|reconstruction/i);
  },
};

export const PendingTepp: Story = {
  args: {
    run: run({ run_kind_code: "analysis_run_tepp", status_code: "analysis_status_pending" }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("status")).toHaveTextContent(/not a calibrated result/i);
    await expect(canvas.getByRole("button", { name: "Start TEPP measurement" })).toBeInTheDocument();
    await expect(canvas.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
  },
};

export const RunningLineageQueued: Story = {
  args: {
    run: run({ run_kind_code: "analysis_run_lineage", status_code: "analysis_status_running" }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("status")).toHaveTextContent(/already queued/i);
    await expect(canvas.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
    await userEvent.click(canvas.getByRole("button", { name: "Refresh this run" }));
  },
};

export const SucceededReportLanding: Story = {
  render: () => (
    <section>
      <h3>Period report · Succeeded · Demo Corp</h3>
      <AnalysisRunNextAction
        run={run({ run_kind_code: "analysis_run_report", status_code: "analysis_status_succeeded" })}
        onStart={() => undefined}
        onRefresh={() => undefined}
      />
      <p role="status">
        Demo Corp is the opened grouping. Read its mean θ and member posts below, then open a post.
      </p>
      <button type="button">Open period report 2026-W02</button>
    </section>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("heading", { name: /Period report · Succeeded · Demo Corp/ })).toBeInTheDocument();
    await expect(canvas.getByRole("status")).toHaveTextContent(/Read its mean θ and member posts/i);
    await expect(canvas.getByRole("button", { name: "Open period report 2026-W02" })).toBeInTheDocument();
    await expect(canvas.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
  },
};

export const CutoffLiveBodyWarning: Story = {
  render: () => (
    <section>
      <p role="status" aria-label="Live body warning">
        This is the live body, not a cutoff snapshot. Compare it with this 2026-01-12 run before you
        treat it as reconstructed evidence.
      </p>
      <CutoffKnownBody
        title="Demo public post"
        body="Ada West at Demo Corp followed up about the delayed shipment."
        writtenAt="2026-01-10T12:00:00Z"
        cutoff="2026-01-12T12:00:00Z"
      />
    </section>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("status", { name: "Live body warning" })).toHaveTextContent(
      /live body, not a cutoff snapshot/i,
    );
    await expect(canvas.getByText("Body this run knew")).toBeInTheDocument();
    await expect(canvas.getByText(/2026-01-10/)).toBeInTheDocument();
    await expect(canvas.getByText(/2026-01-12/)).toBeInTheDocument();
  },
};
