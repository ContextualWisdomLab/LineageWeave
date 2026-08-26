import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AskAgentPanel } from "./App";

describe("AskAgentPanel public verification", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requires explicit consent and keeps public evidence separate", async () => {
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
              cited_post_ids: ["post-1"],
              cited_posts: [{ post_id: "post-1", post_title: "Internal Apollo post" }],
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
              next_action: "Compare the public sources with the cited posts before deciding what to do next.",
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
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      question: "What is Apollo?",
      verify_external: true,
    });
    expect(screen.getByRole("region", { name: "Public verification" })).toBeInTheDocument();
    expect(screen.getByText("Supported by public evidence")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Public Apollo evidence" })).toHaveAttribute(
      "href",
      "https://example.com/apollo",
    );
    expect(screen.getByText("Internal Apollo post")).toBeInTheDocument();
  });

  it("shows an unavailable public-verification result", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ask_job_id: "job-2", job_status_code: "queued" }), {
          status: 202,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ask_job_id: "job-2",
            job_status_code: "succeeded",
            answer: {
              answer_text: "No external judgment was available.",
              cited_post_ids: [],
              cited_posts: [],
              cited_post_evidence: [],
              source_post_ids: [],
              external_verification_status: "external_verification_unavailable",
              external_claims: [],
              next_action: "Retry after the public verification service is available.",
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<AskAgentPanel accessToken="access-token" onOpenPost={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Ask a question"), "Verify Apollo");
    await userEvent.click(screen.getByRole("checkbox", { name: "Check eligible public claims" }));
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(screen.getByText("Public verification is unavailable. Try again later.")).toBeInTheDocument();
    expect(
      screen.getByText("Retry after the public verification service is available."),
    ).toBeInTheDocument();
  });
});
