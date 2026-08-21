import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceNav } from "./WorkspaceNav";

describe("WorkspaceNav", () => {
  it("renders the four workspace destinations and marks the current page", () => {
    render(<WorkspaceNav destination="board" onChange={vi.fn()} />);

    expect(screen.getByRole("navigation")).toHaveAccessibleName("Workspace navigation");
    expect(screen.getByRole("button", { name: "Board" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "Customer master" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("button", { name: "Calendar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask Agent" })).toBeInTheDocument();
  });

  it("reports navigation changes", () => {
    const onChange = vi.fn();
    render(<WorkspaceNav destination="board" onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Calendar" }));
    expect(onChange).toHaveBeenCalledWith("calendar");
  });

  it("hides the admin destination when the account lacks admin permission", () => {
    render(<WorkspaceNav destination="board" onChange={vi.fn()} showAdmin={false} />);

    expect(screen.queryByRole("button", { name: "Admin" })).not.toBeInTheDocument();
  });
});
