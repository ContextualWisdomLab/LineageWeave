import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AuthErrorScreen } from "./AuthErrorScreen";

describe("AuthErrorScreen", () => {
  it("announces a session-expiry message via role=alert and keeps the raw detail visible", () => {
    render(
      <AuthErrorScreen brandName="LineageWeave" message="Token is not active" onRetry={() => {}} />,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Your session has expired.");
    expect(screen.getByText("Token is not active")).toBeInTheDocument();
  });

  it("falls back to a generic message for a non-session auth error", () => {
    render(
      <AuthErrorScreen
        brandName="LineageWeave"
        message="Unexpected error: invalid_client"
        onRetry={() => {}}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("An authentication error occurred.");
  });

  it("calls onRetry when the recovery button is clicked", async () => {
    const onRetry = vi.fn();
    render(<AuthErrorScreen brandName="LineageWeave" message="Token is not active" onRetry={onRetry} />);
    await userEvent.click(screen.getByRole("button", { name: /log in again/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
