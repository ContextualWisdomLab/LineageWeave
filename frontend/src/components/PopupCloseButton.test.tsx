import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PopupCloseButton } from "./PopupCloseButton";

describe("PopupCloseButton", () => {
  it("closes the evidence panel when the buyer clicks close", async () => {
    const onClose = vi.fn();
    render(
      <PopupCloseButton onClose={onClose} label="Close evidence panel" />,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Close evidence panel" }),
    );
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
