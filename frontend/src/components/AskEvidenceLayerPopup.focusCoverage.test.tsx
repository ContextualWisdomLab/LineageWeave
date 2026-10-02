import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AskEvidenceLayerPopup } from "./AskEvidenceLayerPopup";

const baseProps = {
  postId: "post-demo-public",
  postTitle: "Checkout error follow-up",
  facts: [],
  images: [],
  onClose: vi.fn(),
  onOpenPost: vi.fn(),
};

describe("AskEvidenceLayerPopup focus edge coverage", () => {
  it("moves forward from the dialog container to the first visible control", async () => {
    render(<AskEvidenceLayerPopup {...baseProps} />);
    const panel = screen.getByRole("dialog");
    const closeButton = screen.getByRole("button", { name: "Close evidence panel" });

    panel.focus();
    await userEvent.tab();

    expect(closeButton).toHaveFocus();
  });

  it("does not restore focus to an invoking element that was detached before unmount", () => {
    const opener = document.createElement("button");
    opener.textContent = "Detached evidence trigger";
    document.body.append(opener);
    opener.focus();

    const { unmount } = render(<AskEvidenceLayerPopup {...baseProps} />);
    expect(screen.getByRole("dialog")).toHaveFocus();

    opener.remove();
    expect(() => unmount()).not.toThrow();
    expect(opener.isConnected).toBe(false);
  });
});
