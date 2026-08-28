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
    let askedQuestion = "";
    globalThis.fetch = async (_input, init) => {
      requestCount += 1;
      if (requestCount === 1) {
        askedQuestion = JSON.parse(String(init?.body)).question;
        return new Response(JSON.stringify({ ask_job_id: "synthetic-job", job_status_code: "queued" }), { status: 202 });
      }
      return new Response(JSON.stringify({
            ask_job_id: "synthetic-job",
            job_status_code: "succeeded",
            answer: askedQuestion === "Which public claim can I verify?" ? {
              answer_text: "The authorized posts do not contain a claim eligible for public verification.",
              cited_post_ids: [],
              cited_posts: [],
              cited_post_evidence: [],
              source_post_ids: [],
              external_verification_status: "external_verification_no_public_claims",
              external_claims: [],
              next_action: "Ask about a specific claim or narrow the time range, then retry.",
              grounding_status: "live_only",
              limitations: [],
            } : {
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
    await userEvent.type(
      canvas.getByLabelText("Use evidence available by (optional)"),
      "2026-01-15T12:00",
    );
    await userEvent.click(canvas.getByRole("button", { name: "Ask" }));
    await expect(canvas.findByText(/Partially cutoff-grounded/)).resolves.toBeVisible();
    await expect(canvas.getByRole("alert")).toHaveTextContent("Current-only semantic channels were excluded");
    await expect(canvas.getByText(/Retained revision/)).toHaveTextContent("Live source changed later");
  },
};

export const NarrowViewport: Story = {
  ...PartialHistoricalEvidence,
  globals: { viewport: { value: "mobile1", isRotated: false } },
};

export const NoEligiblePublicClaim: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Ask a question"), "Which public claim can I verify?");
    await userEvent.click(canvas.getByRole("checkbox", { name: "Check eligible public claims" }));
    await userEvent.click(canvas.getByRole("button", { name: "Ask" }));
    await expect(canvas.findByText("Ask about a specific claim or narrow the time range, then retry.")).resolves.toBeVisible();
    await expect(canvas.queryByText(/internal|transport|provider|worker/i)).not.toBeInTheDocument();
  },
};

export const NoEligiblePublicClaimNarrow: Story = {
  ...NoEligiblePublicClaim,
  globals: { viewport: { value: "mobile1", isRotated: false } },
};
