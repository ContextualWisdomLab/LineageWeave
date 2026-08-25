import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StatusNotice } from "./StatusNotice";
import { setLocale } from "../i18n";

describe("StatusNotice", () => {
  afterEach(() => {
    setLocale("en");
  });

  it("gives success, unavailable, and retry each a distinct accessible name", () => {
    const { rerender } = render(
      <StatusNotice kind="success" message="Observed events loaded." />,
    );
    const success = screen.getByRole("region").getAttribute("aria-label");

    rerender(<StatusNotice kind="unavailable" message="Calendar projection is missing." />);
    const unavailable = screen.getByRole("region").getAttribute("aria-label");

    rerender(<StatusNotice kind="retry" message="Dashboard evidence did not load." />);
    const retry = screen.getByRole("alert").getAttribute("aria-label");

    expect(new Set([success, unavailable, retry]).size).toBe(3);
    expect(success).toMatch(/^Ready:/);
    expect(unavailable).toMatch(/^Unavailable:/);
    expect(retry).toMatch(/^Retry needed:/);
  });

  it("keeps success and unavailable on a named region and retry on role=alert", () => {
    const { rerender } = render(
      <StatusNotice kind="unavailable" message="이 범위의 일정을 아직 받을 수 없습니다" />,
    );
    expect(screen.getByRole("region", { name: /^Unavailable:/ })).toHaveTextContent(
      "Unavailable",
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    rerender(<StatusNotice kind="retry" message="Dashboard 근거를 불러오지 못했습니다." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Retry needed");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows the next action without inventing evidence", () => {
    render(
      <StatusNotice
        kind="unavailable"
        message="이 범위의 일정을 아직 받을 수 없습니다"
        nextAction="Connect the Naruon calendar projection. Open a commitment below to read that post."
      />,
    );
    expect(screen.getByRole("region", { name: /^Unavailable:/ })).toHaveTextContent(
      "Connect the Naruon calendar projection",
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("retries only on the retry kind", async () => {
    const onRetry = vi.fn();
    const { rerender } = render(
      <StatusNotice kind="unavailable" message="Missing projection." onRetry={onRetry} />,
    );
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();

    rerender(
      <StatusNotice kind="retry" message="Dashboard 근거를 불러오지 못했습니다." onRetry={onRetry} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("localizes the kind label and keeps caller message text", () => {
    setLocale("ko");
    render(
      <StatusNotice kind="unavailable" message="이 범위의 일정을 아직 받을 수 없습니다" />,
    );
    const notice = screen.getByRole("region", { name: /^사용할 수 없음:/ });
    expect(notice).toHaveTextContent("사용할 수 없음");
    expect(notice).toHaveTextContent("이 범위의 일정을 아직 받을 수 없습니다");
    expect(notice.getAttribute("aria-label")).toContain("다음 조치");
  });

  it("hides the decorative glyph from assistive tech", () => {
    render(<StatusNotice kind="success" message="Observed events loaded." />);
    const glyph = screen.getByRole("region", { name: /^Ready:/ }).querySelector(".status-notice-glyph");
    expect(glyph).toHaveAttribute("aria-hidden", "true");
  });
});
