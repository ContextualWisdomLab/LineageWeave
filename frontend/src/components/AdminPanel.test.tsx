import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AdminPanel } from "./AdminPanel";

describe("AdminPanel", () => {
  const baseProps = {
    currentBrandName: "LineageWeave",
    onBrandNameChange: vi.fn(),
    accessToken: "access-token",
    onNavigate: vi.fn(),
    onOpenBoardTool: vi.fn(),
  };

  it("organizes admin routes into an accessible LNB", () => {
    render(<AdminPanel {...baseProps} />);

    expect(screen.getByRole("navigation", { name: "Admin navigation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Post evidence operations/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Lineage rebuild/ })).toBeInTheDocument();
    expect(screen.getByText("10 routes")).toBeInTheDocument();
    expect(screen.getByText("POST /api/lineage/rebuild")).toBeInTheDocument();
  });

  it("hands existing workspace surfaces to their real destination", () => {
    const onNavigate = vi.fn();
    const onOpenBoardTool = vi.fn();
    render(<AdminPanel {...baseProps} onNavigate={onNavigate} onOpenBoardTool={onOpenBoardTool} />);

    fireEvent.click(within(screen.getByRole("navigation", { name: "Admin navigation" })).getByRole("button", { name: /Board & posts/ }));
    expect(onNavigate).toHaveBeenCalledWith("board");

    fireEvent.click(screen.getByRole("button", { name: /Period reports/ }));
    expect(onOpenBoardTool).toHaveBeenCalledWith("reports");
  });

  it("keeps tenant settings in the admin surface", () => {
    render(<AdminPanel {...baseProps} />);

    fireEvent.click(screen.getByRole("button", { name: /Tenant settings/ }));
    expect(screen.getByRole("heading", { name: "Tenant settings" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Tenant brand name" })).toHaveValue("LineageWeave");
  });
});
