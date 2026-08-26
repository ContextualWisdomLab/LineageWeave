import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AskAgentResponse } from "../api";
import { AskAnswerTimeline } from "./AskAnswerTimeline";

const answer: AskAgentResponse = {
  answer_text: "The revised request followed the initial commercial discussion.",
  cited_post_ids: ["post-later", "post-earlier"],
  cited_posts: [
    { post_id: "post-later", post_title: "Revised request" },
    { post_id: "post-earlier", post_title: "Initial discussion" },
  ],
  cited_events: [
    {
      post_id: "post-later",
      post_title: "Revised request",
      observed_at: "2026-08-20T09:00:00Z",
      time_axis_code: "event_occurred_at",
    },
    {
      post_id: "post-earlier",
      post_title: "Initial discussion",
      observed_at: "2026-08-10T09:00:00Z",
      time_axis_code: "created_at",
    },
  ],
  cited_post_evidence: [
    {
      post_id: "post-later",
      facts: [{ kind: "semantic_project", text: "project: Synthetic renewal" }],
    },
  ],
  source_post_ids: ["post-later", "post-earlier"],
};

describe("AskAnswerTimeline", () => {
  it("links citation and chronological event focus in both directions", async () => {
    const user = userEvent.setup();
    render(
      <AskAnswerTimeline
        question="What changed?"
        answer={answer}
        onOpenEvidence={() => undefined}
        onOpenPost={() => undefined}
      />,
    );

    const timeline = screen.getByRole("region", { name: "Answer evidence timeline" });
    const cards = within(timeline).getAllByRole("article");
    expect(cards[0]).toHaveAccessibleName("Evidence 2: Initial discussion");
    expect(cards[1]).toHaveAccessibleName("Evidence 1: Revised request");

    const citation = screen.getByRole("button", { name: "Show event 1: Revised request" });
    const card = screen.getByRole("button", {
      name: "Return to answer citation 1: Revised request",
    });
    await user.click(citation);
    expect(card).toHaveFocus();
    expect(card).toHaveAttribute("aria-pressed", "true");
    await user.click(card);
    expect(citation).toHaveFocus();
    expect(citation).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("status")).toHaveTextContent("Selected evidence: Revised request");
  });

  it("opens the evidence layer and full source from the same authorized card", async () => {
    const user = userEvent.setup();
    const onOpenEvidence = vi.fn();
    const onOpenPost = vi.fn();
    render(
      <AskAnswerTimeline
        question="What changed?"
        answer={answer}
        onOpenEvidence={onOpenEvidence}
        onOpenPost={onOpenPost}
      />,
    );

    await user.click(screen.getAllByRole("button", { name: "View evidence" })[0]);
    expect(onOpenEvidence).toHaveBeenCalledWith("post-earlier");
    await user.click(screen.getByRole("button", { name: "Open post: Revised request" }));
    expect(onOpenPost).toHaveBeenCalledWith("post-later");
  });

  it("names absent time instead of borrowing a lineage timestamp", () => {
    render(
      <AskAnswerTimeline
        question="What changed?"
        answer={{
          ...answer,
          cited_events: [{ ...answer.cited_events![0], observed_at: null, time_axis_code: null }],
          cited_posts: [answer.cited_posts![0]],
        }}
        onOpenEvidence={() => undefined}
        onOpenPost={() => undefined}
      />,
    );

    expect(screen.getByText("Observed time unavailable")).toBeInTheDocument();
  });
});
