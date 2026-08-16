import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AnalysisRunListButton } from "./AnalysisRunListButton";

describe("AnalysisRunListButton", () => {
  it("opens the named run when the buyer clicks the caption", async () => {
    const onOpen = vi.fn();
    render(
      <AnalysisRunListButton
        caption="Lineage reconstruction · Pending · Demo Corp"
        nextAction="Open this run to confirm which posts it will use. Reconstruction has not started yet."
        documentCountLabel="3 documents"
        onOpen={onOpen}
      />,
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: "Open analysis run: Lineage reconstruction · Pending · Demo Corp",
      }),
    );
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(screen.getByText("3 documents")).toBeInTheDocument();
  });

  it("keeps pending TEPP copy from claiming a calibrated measurement", () => {
    render(
      <AnalysisRunListButton
        caption="TEPP measurement · Pending · Demo Corp"
        nextAction="Open this run to confirm which posts TEPP will measure. Measurement has not started yet — this is not a calibrated result."
        onOpen={() => undefined}
      />,
    );
    expect(screen.getByText(/not a calibrated result/)).toBeInTheDocument();
    expect(screen.queryByText(/reconstruction/i)).not.toBeInTheDocument();
  });
});
