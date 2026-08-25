import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AskAgentPanel } from "./App";

describe("AskAgentPanel public verification", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps public verification separate and renders cutoff provenance", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ ask_job_id: "job-1", job_status_code: "queued" }),
          { status: 202, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ask_job_id: "job-1",
            job_status_code: "succeeded",
            answer: {
              answer_text: "Apollo is described by the internal cited post.",
              cited_post_ids: ["post-1", "post-2"],
              cited_posts: [{
                post_id: "post-1",
                post_title: "Internal Apollo post",
                source_post_revision_id: "revision-1",
                evidence_available_at: "2026-01-10T00:00:00Z",
                knowledge_cutoff: "2026-01-15T03:00:00Z",
                live_changed_after_cutoff: true,
                unavailable_channels: ["knowledge_graph"],
              }, {
                post_id: "post-2",
                post_title: "Retained post without timestamp",
                source_post_revision_id: "revision-2",
                evidence_available_at: null,
                knowledge_cutoff: "2026-01-15T03:00:00Z",
                live_changed_after_cutoff: false,
                unavailable_channels: [],
              }],
              cited_post_evidence: [],
              source_post_ids: ["post-1"],
              external_verification_status: "external_verification_completed",
              external_claims: [
                {
                  claim_text: "project: Apollo",
                  claim_kind: "semantic_project",
                  status_code: "claim_supported",
                  rationale: "A bounded public source corroborates the claim.",
                  source_post_ids: ["post-1"],
                  evidence: [
                    {
                      title: "Public Apollo evidence",
                      url: "https://example.com/apollo",
                      snippet: "Apollo is a project.",
                    },
                  ],
                },
              ],
              next_action: "Inspect public evidence separately before any governed graph review.",
              knowledge_cutoff: "2026-01-15T03:00:00Z",
              grounding_status: "fully_cutoff_grounded",
              limitations: [],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<AskAgentPanel accessToken="access-token" onOpenPost={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Ask a question"), "What is Apollo?");
    await userEvent.click(
      screen.getByRole("checkbox", { name: "Check eligible public claims" }),
    );
    await userEvent.type(
      screen.getByLabelText("Knowledge cutoff (optional)"),
      "2026-01-15T12:00",
    );
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      question: "What is Apollo?",
      verify_external: true,
      knowledge_cutoff: new Date("2026-01-15T12:00").toISOString(),
    });
    expect(screen.getByRole("region", { name: "Public verification" })).toBeInTheDocument();
    expect(screen.getByText("Supported by public evidence")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Public Apollo evidence" })).toHaveAttribute(
      "href",
      "https://example.com/apollo",
    );
    const timestampedPost = screen.getByText("Internal Apollo post").closest("li");
    expect(timestampedPost).not.toBeNull();
    expect(screen.getByText(/Fully cutoff-grounded/)).toBeInTheDocument();
    expect(within(timestampedPost!).getByText(/Retained revision/)).toHaveTextContent(
      "Live source changed later",
    );
    const missingTimestampPost = screen
      .getByText("Retained post without timestamp")
      .closest("li");
    expect(missingTimestampPost).not.toBeNull();
    expect(within(missingTimestampPost!).getByText("Retained revision").textContent).toBe(
      "Retained revision",
    );
  });
});
