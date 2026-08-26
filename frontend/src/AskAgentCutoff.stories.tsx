import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { AskAgentPanel } from "./App";
import { getLocale, setLocale } from "./i18n";
import "./App.css";

const meta = {
  title: "Ask Agent/Knowledge cutoff",
  component: AskAgentPanel,
  args: { accessToken: "synthetic-token", onOpenPost: () => undefined },
  parameters: { layout: "fullscreen" },
  beforeEach: () => {
    const previousFetch = globalThis.fetch;
    const previousLocale = getLocale();
    setLocale("en");
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
              public_claim_verification: {
                status_code: "claim_supported",
                next_action: "Public web evidence supports this claim. Open that post.",
                claims: [{
                  public_claim_envelope_id: "synthetic-claim",
                  source_post_id: "synthetic-post",
                  source_post_title: "Retained Apollo revision",
                  claim_kind_code: "claim_public_event",
                  subject_label: "Apollo",
                  claim_text: "Apollo appeared in a published event notice.",
                  status_code: "claim_supported",
                  external_evidence_urls: ["https://example.com/apollo"],
                  next_action: "Public web evidence supports this claim. Open that post.",
                }],
              },
              knowledge_cutoff: "2026-01-15T03:00:00Z",
              grounding_status: "partially_cutoff_grounded",
              limitations: ["Current-only semantic channels were excluded from this historical answer."],
            },
          }), { status: 200 });
    };
    return () => {
      globalThis.fetch = previousFetch;
      setLocale(previousLocale);
    };
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
    await expect(
      canvas.getAllByText("Public web evidence supports this claim. Open that post."),
    ).toHaveLength(2);
  },
};

export const NarrowViewport: Story = {
  ...PartialHistoricalEvidence,
  globals: { viewport: { value: "mobile1", isRotated: false } },
};
