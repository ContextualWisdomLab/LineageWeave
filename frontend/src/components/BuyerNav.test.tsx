import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BuyerNav } from "./BuyerNav";

describe("BuyerNav", () => {
  it("renders the four buyer destinations and marks the current page", () => {
    render(<BuyerNav destination="board" onChange={vi.fn()} />);

    expect(screen.getByRole("navigation")).toHaveAccessibleName("Buyer navigation");
    expect(screen.getByRole("button", { name: "Board" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "Customer master" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("button", { name: "Calendar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask Agent" })).toBeInTheDocument();
  });

  it("reports navigation changes", () => {
    const onChange = vi.fn();
    render(<BuyerNav destination="board" onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Calendar" }));
    expect(onChange).toHaveBeenCalledWith("calendar");
  });
});
