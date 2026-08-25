import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { AskAgentPanel } from "./App";
import "./App.css";

const meta = {
  title: "Ask Agent/Knowledge cutoff",
  component: AskAgentPanel,
  args: { accessToken: "synthetic-token", onOpenPost: () => undefined },
  parameters: { layout: "fullscreen" },
  beforeEach: () => {
    const previousFetch = globalThis.fetch;
    let requestCount = 0;
    globalThis.fetch = async () => {
      requestCount += 1;
      return requestCount === 1
        ? new Response(JSON.stringify({ ask_job_id: "synthetic-job", job_status_code: "queued" }), { status: 202 })
        : new Response(JSON.stringify({
            ask_job_id: "synthetic-job",
            job_status_code: "succeeded",
            answer: {
              answer_text: "The retained revision supports the historical answer.",
              cited_post_ids: ["synthetic-post"],
              cited_posts: [{
                post_id: "synthetic-post",
                post_title: "Retained Apollo revision",
                source_post_revision_id: "synthetic-revision",
                evidence_available_at: "2026-01-10T00:00:00Z",
                knowledge_cutoff: "2026-01-15T03:00:00Z",
                live_changed_after_cutoff: true,
              }],
              cited_post_evidence: [],
              source_post_ids: ["synthetic-post"],
              knowledge_cutoff: "2026-01-15T03:00:00Z",
              grounding_status: "partially_cutoff_grounded",
              limitations: ["Current-only semantic channels were excluded from this historical answer."],
            },
          }), { status: 200 });
    };
    return () => { globalThis.fetch = previousFetch; };
  },
} satisfies Meta<typeof AskAgentPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const PartialHistoricalEvidence: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Ask a question"), "What was known about Apollo?");
    await userEvent.type(canvas.getByLabelText("Knowledge cutoff (optional)"), "2026-01-15T12:00");
    await userEvent.click(canvas.getByRole("button", { name: "Ask" }));
    await expect(canvas.findByText(/Partially cutoff-grounded/)).resolves.toBeVisible();
    await expect(canvas.getByRole("alert")).toHaveTextContent("Current-only semantic channels were excluded");
    await expect(canvas.getByText(/Retained revision/)).toHaveTextContent("Live source changed later");
  },
};

export const NarrowViewport: Story = {
  ...PartialHistoricalEvidence,
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
