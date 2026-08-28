import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ANALYST_GNB_LABELS, initialWorkspaceDestination } from "../gnbChrome";
import { setLocale } from "../i18n";
import { WorkspaceNav } from "./WorkspaceNav";

afterEach(() => {
  setLocale("en");
});

describe("WorkspaceNav", () => {
  it("opens shared post links on the board before rendering the dashboard", () => {
    expect(initialWorkspaceDestination("?post=synthetic-post", false)).toBe("board");
    expect(initialWorkspaceDestination("", false)).toBe("dashboard");
  });

  it("renders the Dashboard and five analyst destinations and marks the current page", () => {
    render(<WorkspaceNav destination="board" onChange={vi.fn()} />);

    const nav = screen.getByRole("navigation");
    expect(nav).toHaveAccessibleName("Workspace navigation");
    const buttons = within(nav).getAllByRole("button");
    expect(buttons.map((button) => button.textContent)).toEqual(ANALYST_GNB_LABELS);
    expect(screen.getByRole("button", { name: "Board" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "Customer master" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("button", { name: "Calendar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask Agent" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Admin" })).not.toBeInTheDocument();
    expect(nav.textContent).not.toMatch(/Buyer|Cubee/i);
  });

  it.each([
    ["en", ["Dashboard", "External information", "Board", "Customer master", "Calendar", "Ask Agent"]],
    ["ko", ["대시보드", "외부 정보", "게시판", "고객 마스터", "캘린더", "에이전트에게 질문"]],
    ["zh", ["仪表板", "外部信息", "看板", "客户主数据", "日历", "询问智能助手"]],
    ["ja", ["ダッシュボード", "外部情報", "掲示板", "顧客マスター", "カレンダー", "エージェントに質問"]],
    ["vi", ["Bảng điều khiển", "Thông tin bên ngoài", "Bảng tin", "Danh mục khách hàng", "Lịch", "Hỏi trợ lý"]],
  ] as const)("localizes every GNB label in %s", (locale, expected) => {
    setLocale(locale);
    render(<WorkspaceNav destination="ask" onChange={vi.fn()} />);

    const nav = screen.getByRole("navigation");
    expect(within(nav).getAllByRole("button").map((button) => button.textContent)).toEqual(expected);
    expect(nav.textContent).not.toMatch(/Buyer|Cubee/);
  });

  it("does not advertise Admin, Weekly VOC, or newspaper as GNB items", () => {
    render(<WorkspaceNav destination="admin" onChange={vi.fn()} />);

    const nav = screen.getByRole("navigation");
    expect(within(nav).queryByRole("button", { name: /Admin|관리자/i })).not.toBeInTheDocument();
    expect(nav.textContent).not.toMatch(/Weekly VOC|newspaper|주간|월간/i);
    expect(screen.queryByRole("button", { name: "Board" })).not.toHaveAttribute("aria-current");
  });

  it("reports navigation changes", () => {
    const onChange = vi.fn();
    render(<WorkspaceNav destination="board" onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Calendar" }));
    expect(onChange).toHaveBeenCalledWith("calendar");
  });
});
