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
            tags: ["screenshot", "error"],
          },
        ]}
        onClose={vi.fn()}
        onOpenPost={vi.fn()}
      />,
    );

    expect(screen.getByRole("dialog", { name: "Checkout error follow-up" })).toBeInTheDocument();
    expect(screen.getByText(/project: Checkout revamp/)).toBeInTheDocument();
    expect(screen.getByText("Screenshot of the checkout error")).toBeInTheDocument();
    expect(screen.getByText(/Error code 500 on checkout/)).toBeInTheDocument();
    expect(screen.getByText(/Project:/).closest("li")).toHaveTextContent(
      "Project: project: Checkout revamp | evidence: Body evidence",
    );
    expect(screen.getByText("Screenshot of the checkout error").closest("li")).toHaveTextContent(
      "Screenshot of the checkout error · Error code 500 on checkout · Image tags: screenshot, error",
    );
    expect(
      screen.getByRole("list", { name: "Checkout error follow-up Evidence facts" }),
    ).toBeInTheDocument();
  });

  it("names the event-time axis so a click still opens that post", () => {
    render(
      <AskEvidenceLayerPopup
        {...baseProps}
        facts={[{ kind: "time_axis", text: "time axis: event occurred at" }]}
        images={[]}
        onClose={vi.fn()}
        onOpenPost={vi.fn()}
      />,
    );

    expect(screen.getByText(/^Date:/)).toBeInTheDocument();
    expect(screen.getByText("time axis: event occurred at")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open post: Checkout error follow-up" }),
    ).toBeInTheDocument();
  });

  it("shows an explicit placeholder when the citation has no persisted evidence", () => {
    render(
      <AskEvidenceLayerPopup {...baseProps} facts={[]} images={[]} onClose={vi.fn()} onOpenPost={vi.fn()} />,
    );
    expect(
      screen.getByText("No evidence is available here. Open the linked post to review its details."),
    ).toBeInTheDocument();
  });

  it("uses the untitled fallback when an image caption is blank", () => {
    render(
      <AskEvidenceLayerPopup
        {...baseProps}
        facts={[]}
        images={[{ unit_index: 0, caption: "", extracted_text: null, tags: [] }]}
        onClose={vi.fn()}
        onOpenPost={vi.fn()}
      />,
    );
    expect(screen.getByText("Untitled image")).toBeInTheDocument();
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

  it("closes the evidence layer before opening the cited post", async () => {
    const onClose = vi.fn();
    const onOpenPost = vi.fn();
    render(
      <AskEvidenceLayerPopup
        {...baseProps}
        facts={[]}
        images={[]}
        onClose={onClose}
        onOpenPost={onOpenPost}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Open post: Checkout error follow-up" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onOpenPost).toHaveBeenCalledWith("post-demo-public");
    expect(onClose.mock.invocationCallOrder[0]).toBeLessThan(onOpenPost.mock.invocationCallOrder[0]);
  });

  it("moves initial focus onto the dialog panel", () => {
    render(
      <AskEvidenceLayerPopup {...baseProps} facts={[]} images={[]} onClose={vi.fn()} onOpenPost={vi.fn()} />,
    );
    expect(screen.getByRole("dialog")).toHaveFocus();
  });

  it("contains Tab and Shift+Tab focus within the modal layer", async () => {
    render(
      <AskEvidenceLayerPopup {...baseProps} facts={[]} images={[]} onClose={vi.fn()} onOpenPost={vi.fn()} />,
    );
    const closeButton = screen.getByRole("button", { name: "Close evidence panel" });
    const openPostButton = screen.getByRole("button", { name: "Open post: Checkout error follow-up" });

    openPostButton.focus();
    await userEvent.tab();
    expect(closeButton).toHaveFocus();

    closeButton.focus();
    await userEvent.tab({ shift: true });
    expect(openPostButton).toHaveFocus();
  });

  it("excludes collapsed controls from the modal focus order", async () => {
    render(
      <AskEvidenceLayerPopup {...baseProps} facts={[]} images={[]} onClose={vi.fn()} onOpenPost={vi.fn()} />,
    );
    const panel = screen.getByRole("dialog");
    const collapsed = document.createElement("details");
    const collapsedButton = document.createElement("button");
    collapsedButton.textContent = "Collapsed action";
    collapsed.append(collapsedButton);
    panel.append(collapsed);

    panel.focus();
    await userEvent.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Open post: Checkout error follow-up" })).toHaveFocus();
    expect(collapsedButton).not.toHaveFocus();
  });

  it("returns focus to the element that invoked the modal when the layer unmounts", () => {
    const opener = document.createElement("button");
    opener.textContent = "View evidence";
    document.body.append(opener);
    opener.focus();

    const { unmount } = render(
      <AskEvidenceLayerPopup {...baseProps} facts={[]} images={[]} onClose={vi.fn()} onOpenPost={vi.fn()} />,
    );
    expect(screen.getByRole("dialog")).toHaveFocus();

    unmount();
    expect(opener).toHaveFocus();
    opener.remove();
  });
});
