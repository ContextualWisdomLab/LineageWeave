import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CutoffKnownBody } from "./CutoffKnownBody";

describe("CutoffKnownBody", () => {
  it("tells the operator to compare the cutoff-known text with the live body", () => {
    render(
      <CutoffKnownBody
        title="Demo public post"
        body="January follow-up about the delayed shipment."
        writtenAt="2026-01-10T12:00:00Z"
        cutoff="2026-01-12T12:00:00Z"
      />,
    );
    expect(screen.getByRole("heading", { name: "Body this run knew" })).toBeInTheDocument();
    expect(screen.getByText("January follow-up about the delayed shipment.")).toBeInTheDocument();
    expect(
      screen.getByText(/written 2026-01-10, known at cutoff 2026-01-12/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Compare this text with the live body below/)).toBeInTheDocument();
  });
});
