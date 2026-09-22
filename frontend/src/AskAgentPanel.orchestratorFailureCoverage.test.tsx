import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AskAgentPanel } from "./App";

describe("AskAgentPanel orchestrator failure boundary", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps saved evidence available when the released orchestrator is temporarily unavailable", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "orchestrator unavailable" }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<AskAgentPanel accessToken="access-token" onOpenPost={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Ask a question"), "What changed in Apollo?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(
      await screen.findByText(
        "Ask Agent is temporarily unavailable. Saved evidence is still available.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask" })).toBeEnabled();
  });
});
