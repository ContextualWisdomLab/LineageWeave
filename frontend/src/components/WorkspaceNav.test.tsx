import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ANALYST_GNB_LABELS, initialWorkspaceDestination } from "../gnbChrome";
import { SUPPORTED_LOCALES, setLocale } from "../i18n";
import { WorkspaceNav } from "./WorkspaceNav";

afterEach(() => {
  setLocale("en");
});

describe("WorkspaceNav", () => {
  it("opens shared post links on the board before rendering the dashboard", () => {
    expect(initialWorkspaceDestination("?post=synthetic-post", false)).toBe("board");
    expect(initialWorkspaceDestination("", false)).toBe("dashboard");
  });

  it("renders the Dashboard and four analyst destinations and marks the current page", () => {
    render(<WorkspaceNav destination="board" onChange={vi.fn()} />);

    const nav = screen.getByRole("navigation");
    expect(nav).toHaveAccessibleName("Workspace navigation");
    const buttons = within(nav).getAllByRole("button");
    expect(buttons.map((button) => button.textContent)).toEqual(ANALYST_GNB_LABELS);
    expect(screen.getByRole("button", { name: "게시판" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "고객 마스터" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("button", { name: "달력" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask Agent" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Admin" })).not.toBeInTheDocument();
    expect(nav.textContent).not.toMatch(/Buyer|Cubee|Customer master/i);
  });

  it.each(SUPPORTED_LOCALES)("keeps the four Korean GNB labels in %s", (locale) => {
    setLocale(locale);
    render(<WorkspaceNav destination="ask" onChange={vi.fn()} />);

    const nav = screen.getByRole("navigation");
    expect(within(nav).getAllByRole("button").map((button) => button.textContent)).toEqual([
      "Dashboard",
      "게시판",
      "고객 마스터",
      "달력",
      "Ask Agent",
    ]);
    expect(screen.queryByRole("button", { name: "Board" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Customer master" })).not.toBeInTheDocument();
    expect(nav.textContent).not.toMatch(/Buyer|Cubee/);
  });

  it("does not advertise Admin, Weekly VOC, or newspaper as GNB items", () => {
    render(<WorkspaceNav destination="admin" onChange={vi.fn()} />);

    const nav = screen.getByRole("navigation");
    expect(within(nav).queryByRole("button", { name: /Admin|관리자/i })).not.toBeInTheDocument();
    expect(nav.textContent).not.toMatch(/Weekly VOC|newspaper|주간|월간/i);
    expect(screen.queryByRole("button", { name: "게시판" })).not.toHaveAttribute("aria-current");
  });

  it("reports navigation changes", () => {
    const onChange = vi.fn();
    render(<WorkspaceNav destination="board" onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "달력" }));
    expect(onChange).toHaveBeenCalledWith("calendar");
  });
});
