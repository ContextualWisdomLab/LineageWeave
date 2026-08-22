import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AskEvidenceLayerPopup } from "./AskEvidenceLayerPopup";

const baseProps = {
  postId: "post-demo-public",
  postTitle: "Checkout error follow-up",
};

describe("AskEvidenceLayerPopup", () => {
  it("renders text and image evidence for the cited post", () => {
    render(
      <AskEvidenceLayerPopup
        {...baseProps}
        facts={[{ kind: "semantic_project", text: "project: Checkout revamp | evidence: Body evidence" }]}
        images={[
          {
            unit_index: 1,
            caption: "Screenshot of the checkout error",
            extracted_text: "Error code 500 on checkout",
          },
        ]}
        onClose={vi.fn()}
        onOpenPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("dialog", { name: "Checkout error follow-up" })).toBeInTheDocument();
    expect(screen.getByText(/project: Checkout revamp/)).toBeInTheDocument();
    expect(screen.getByText("Screenshot of the checkout error")).toBeInTheDocument();
    expect(screen.getByText("Error code 500 on checkout")).toBeInTheDocument();
  });

  it("shows an explicit placeholder when the citation has no persisted evidence", () => {
    render(
      <AskEvidenceLayerPopup {...baseProps} facts={[]} images={[]} onClose={vi.fn()} onOpenPost={vi.fn()} />,
    );
    expect(
      screen.getByText("No persisted evidence is available for this citation."),
    ).toBeInTheDocument();
  });

  it("closes on backdrop click, close button click, and Escape, but not on panel click", async () => {
    const onClose = vi.fn();
    const { container } = render(
      <AskEvidenceLayerPopup {...baseProps} facts={[]} images={[]} onClose={onClose} onOpenPost={vi.fn()} />,
    );

    await userEvent.click(screen.getByRole("dialog"));
    expect(onClose).not.toHaveBeenCalled();

    const backdrop = container.querySelector(".popup-backdrop") as HTMLElement;
    await userEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Close evidence panel" }));
    expect(onClose).toHaveBeenCalledTimes(2);

    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(3);
  });

  it("opens the cited post from the layer", async () => {
    const onOpenPost = vi.fn();
    render(
      <AskEvidenceLayerPopup
        {...baseProps}
        facts={[]}
        images={[]}
        onClose={vi.fn()}
        onOpenPost={onOpenPost}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Open post: Checkout error follow-up" }));
    expect(onOpenPost).toHaveBeenCalledWith("post-demo-public");
  });

  it("moves initial focus onto the dialog panel", () => {
    render(
      <AskEvidenceLayerPopup {...baseProps} facts={[]} images={[]} onClose={vi.fn()} onOpenPost={vi.fn()} />,
    );
    expect(screen.getByRole("dialog")).toHaveFocus();
  });
});
