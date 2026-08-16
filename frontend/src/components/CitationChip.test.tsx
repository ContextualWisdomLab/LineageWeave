import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CitationChip } from "./CitationChip";

describe("CitationChip", () => {
  it("opens the cited post when the buyer clicks the chip", async () => {
    const onOpenEvidence = vi.fn();
    render(
      <CitationChip
        postId="post-demo-public"
        postTitle="Demo public post"
        onOpenEvidence={onOpenEvidence}
      />,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Open evidence: Demo public post" }),
    );
    expect(onOpenEvidence).toHaveBeenCalledWith("post-demo-public");
  });
});
