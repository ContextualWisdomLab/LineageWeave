import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { EvidenceStatusMark } from "./EvidenceStatusMark";
import { setLocale } from "../i18n";

describe("EvidenceStatusMark", () => {
  afterEach(() => {
    setLocale("en");
  });

  it("gives evidence, inference, and prediction each a distinct accessible label", () => {
    const { rerender } = render(<EvidenceStatusMark status="evidence" />);
    const evidenceLabel = screen.getByRole("img").getAttribute("aria-label");

    rerender(<EvidenceStatusMark status="inference" />);
    const inferenceLabel = screen.getByRole("img").getAttribute("aria-label");

    rerender(<EvidenceStatusMark status="prediction" />);
    const predictionLabel = screen.getByRole("img").getAttribute("aria-label");

    // The three statuses must never be indistinguishable by text alone
    // (WCAG 1.4.1 -- this is the non-color channel, not a decoration).
    expect(new Set([evidenceLabel, inferenceLabel, predictionLabel]).size).toBe(3);
    expect(evidenceLabel).toMatch(/^Evidence:/);
    expect(inferenceLabel).toMatch(/^Inference:/);
    expect(predictionLabel).toMatch(/^Prediction:/);
  });

  it("never lets a prediction's copy claim it is confirmed fact", () => {
    render(<EvidenceStatusMark status="prediction" />);
    const label = screen.getByRole("img").getAttribute("aria-label") ?? "";
    expect(label).toMatch(/unconfirmed/i);
  });

  it("renders visible text, not an icon-only mark", () => {
    render(<EvidenceStatusMark status="evidence" />);
    expect(screen.getByRole("img")).toHaveTextContent("Evidence");
  });

  it("hides the decorative glyph from assistive tech", () => {
    render(<EvidenceStatusMark status="inference" />);
    const glyph = screen.getByRole("img").querySelector(".evidence-status-glyph");
    expect(glyph).toHaveAttribute("aria-hidden", "true");
  });

  it("localizes the label and description together", () => {
    setLocale("ko");
    render(<EvidenceStatusMark status="evidence" />);
    const status = screen.getByRole("img");
    expect(status).toHaveTextContent("증거");
    expect(status.getAttribute("aria-label")).toContain("직접 관찰");
  });
});
