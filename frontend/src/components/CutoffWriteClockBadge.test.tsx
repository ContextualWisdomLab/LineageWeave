import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CutoffWriteClockBadge } from "./CutoffWriteClockBadge";

describe("CutoffWriteClockBadge", () => {
  it("tells the operator the live title was rewritten after the run", () => {
    render(<CutoffWriteClockBadge />);
    expect(screen.getByText("Updated after cutoff")).toBeInTheDocument();
  });
});
