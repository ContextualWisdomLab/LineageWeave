import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BackendError, type AskAgentResponse } from "../api";
import {
  AskAgentWorkspace,
  AskAgentWorkspaceView,
  GLOBAL_ASK_SESSION_STORAGE_KEY,
} from "./AskAgentWorkspace";

const answer: AskAgentResponse = {
  session_id: "session-1",
  answer_text: "The cited project is supported by the stored semantic evidence.",
  cited_post_ids: ["post-2"],
  cited_posts: [{ post_id: "post-2", post_title: "Linked post" }],
  cited_post_evidence: [
    {
      post_id: "post-2",
      facts: [
        { kind: "semantic_project", text: "project: Semantic project | evidence: Body evidence" },
      ],
    },
  ],
  source_post_ids: ["post-1", "post-2"],
  timeline: [
    {
      post_id: "post-1",
      post_title: "Public post",
      occurred_at: "2026-01-01T00:00:00Z",
      timeline_kind: "lineage_anchor",
    },
  ],
};

beforeEach(() => {
  window.sessionStorage.clear();
});

describe("AskAgentWorkspace", () => {
  it("submits an evidence-grounded question, focuses the answer, and opens sources", async () => {
    const request = vi.fn().mockResolvedValue(answer);
    const onOpenPost = vi.fn();
    render(
      <AskAgentWorkspace
        accessToken="access-token"
        onOpenPost={onOpenPost}
        request={request}
      />,
    );

    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    const result = await screen.findByRole("article", { name: "Answer" });
    expect(result).toHaveFocus();
    expect(result).toHaveTextContent(answer.answer_text);
    expect(within(result).getByRole("list", { name: "Evidence facts" })).toHaveTextContent(
      "Semantic project",
    );
    expect(within(result).getByRole("list", { name: "Event Lineage timeline" })).toHaveTextContent(
      "2026-01-01T00:00:00Z",
    );

    await userEvent.click(within(result).getByRole("button", { name: "Open cited post: Linked post" }));
    expect(onOpenPost).toHaveBeenCalledWith("post-2");
    expect(window.sessionStorage.getItem(GLOBAL_ASK_SESSION_STORAGE_KEY)).toBe("session-1");
  });

  it.each([404, 409])("retries once without an invalid saved session after %i", async (status) => {
    window.sessionStorage.setItem(GLOBAL_ASK_SESSION_STORAGE_KEY, "stale-session");
    const request = vi
      .fn()
      .mockRejectedValueOnce(new BackendError("/api/ask", status, "Global Ask session invalid"))
      .mockResolvedValueOnce(answer);
    render(
      <AskAgentWorkspace
        accessToken="access-token"
        onOpenPost={() => undefined}
        request={request}
      />,
    );

    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText(answer.answer_text)).toBeInTheDocument();

    expect(request).toHaveBeenNthCalledWith(1, "access-token", "Which project?", "stale-session");
    expect(request).toHaveBeenNthCalledWith(2, "access-token", "Which project?");
    expect(window.sessionStorage.getItem(GLOBAL_ASK_SESSION_STORAGE_KEY)).toBe("session-1");
  });

  it("hides the previous answer while a replacement answer is pending", async () => {
    let resolveSecond: (value: AskAgentResponse) => void = () => undefined;
    const pending = new Promise<AskAgentResponse>((resolve) => {
      resolveSecond = resolve;
    });
    const request = vi.fn().mockResolvedValueOnce(answer).mockReturnValueOnce(pending);
    render(
      <AskAgentWorkspace
        accessToken="access-token"
        onOpenPost={() => undefined}
        request={request}
      />,
    );

    const textbox = screen.getByRole("textbox", { name: "Ask a question" });
    await userEvent.type(textbox, "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText(answer.answer_text)).toBeInTheDocument();

    await userEvent.clear(textbox);
    await userEvent.type(textbox, "Which person?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(screen.getByRole("button", { name: "Asking..." })).toBeDisabled();
    expect(screen.queryByText(answer.answer_text)).not.toBeInTheDocument();

    resolveSecond(answer);
    expect(await screen.findByText(answer.answer_text)).toBeInTheDocument();
  });
});

describe("AskAgentWorkspaceView keyboard contract", () => {
  it("submits Enter, preserves Shift+Enter, and ignores an IME composition Enter", () => {
    const onSubmit = vi.fn();
    render(
      <AskAgentWorkspaceView
        question="Which project?"
        knowledgeCutoff=""
        answer={null}
        error={null}
        asking={false}
        onQuestionChange={() => undefined}
        onKnowledgeCutoffChange={() => undefined}
        onSubmit={onSubmit}
        onOpenPost={() => undefined}
      />,
    );
    const textbox = screen.getByRole("textbox", { name: "Ask a question" });

    fireEvent.keyDown(textbox, { key: "Enter", shiftKey: true });
    fireEvent.keyDown(textbox, { key: "Enter", isComposing: true });
    expect(onSubmit).not.toHaveBeenCalled();

    fireEvent.keyDown(textbox, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("keeps a visible, non-submit error state", async () => {
    render(
      <AskAgentWorkspaceView
        question="Which project?"
        knowledgeCutoff=""
        answer={null}
        error="Ask Agent is temporarily unavailable. Saved evidence is still available."
        asking={false}
        onQuestionChange={() => undefined}
        onKnowledgeCutoffChange={() => undefined}
        onSubmit={() => undefined}
        onOpenPost={() => undefined}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Saved evidence is still available.");
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Ask a question" })).toBeEnabled());
  });
});
