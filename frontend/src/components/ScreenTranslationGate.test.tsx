import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScreenTranslationGate } from "./ScreenTranslationGate";

describe("ScreenTranslationGate", () => {
  it("announces loading without exposing untranslated screen content", () => {
    render(<ScreenTranslationGate state="loading" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading this screen");
  });

  it("offers one retry action when published copy is unavailable", () => {
    const onRetry = vi.fn();
    render(<ScreenTranslationGate state="retry" onRetry={onRetry} />);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
