import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AnalysisRunRequestButton } from "./AnalysisRunRequestButton";

describe("AnalysisRunRequestButton", () => {
  it("records a lineage request when the buyer clicks", async () => {
    const onRequest = vi.fn();
    render(<AnalysisRunRequestButton requesting={false} onRequest={onRequest} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Request a lineage reconstruction" }),
    );
    expect(onRequest).toHaveBeenCalledTimes(1);
  });

  it("stays idle while the cutoff bag is being recorded", () => {
    render(<AnalysisRunRequestButton requesting={true} onRequest={() => undefined} />);
    expect(screen.getByRole("button", { name: "Request a lineage reconstruction" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Request a lineage reconstruction" })).toHaveTextContent(
      "Recording the run...",
    );
  });
});
