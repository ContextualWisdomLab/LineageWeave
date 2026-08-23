import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ExceptionAlert, SummaryStatus } from "./SummaryStatus";

describe("SummaryStatus exception surface", () => {
  it("announces unavailable failures as an alert with next-action copy and a retry control", async () => {
    const onRetry = vi.fn();
    render(
      <SummaryStatus
        kind="unavailable"
        title="This board could not be loaded."
        description="Retry loading posts, or choose another destination."
        detail="The previous saved board remains unchanged."
        retryLabel="Retry"
        onRetry={onRetry}
      />,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("This board could not be loaded.");
    expect(alert).toHaveTextContent("Retry loading posts, or choose another destination.");
    expect(alert).toHaveTextContent("The previous saved board remains unchanged.");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("keeps processing and empty states as status, not alert", () => {
    const { rerender } = render(
      <SummaryStatus
        kind="processing"
        title="Summary is being prepared."
        description="The source evidence is still being analyzed."
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Summary is being prepared.");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    rerender(
      <SummaryStatus
        kind="empty"
        title="No saved summary exists for this record."
        description="The source record is available, but no summary has been saved."
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("No saved summary exists for this record.");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders the inline form-field exception without leaking a raw 5xx payload", () => {
    render(
      <ExceptionAlert
        title="Copyright year must be an integer."
        description="Correct the highlighted fields, then retry."
        variant="inline"
      />,
    );
    const alert = screen.getByRole("alert");
    expect(alert.className).toMatch(/summary-status-inline/);
    expect(alert).toHaveTextContent("Copyright year must be an integer.");
    expect(alert).toHaveTextContent("Correct the highlighted fields, then retry.");
    expect(alert).not.toHaveTextContent("Internal Server Error");
  });

  it("exposes a log-in control for auth failure", async () => {
    const onAction = vi.fn();
    render(
      <ExceptionAlert
        title="Sign-in could not be completed."
        description="Log in again to open the workspace."
        retryLabel="Log in"
        onRetry={onAction}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Sign-in could not be completed.");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it("names continue-with-saved-evidence as the next action", async () => {
    const onRetry = vi.fn();
    render(
      <ExceptionAlert
        title="Source evidence is unavailable. Continue with the saved answer."
        description="Retry opening this source, or keep reading the saved answer."
        retryLabel="Retry evidence"
        onRetry={onRetry}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Continue with the saved answer");
    await userEvent.click(screen.getByRole("button", { name: "Retry evidence" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
