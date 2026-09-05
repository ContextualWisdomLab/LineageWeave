import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScreenTranslationGate } from "./ScreenTranslationGate";

describe("ScreenTranslationGate", () => {
  it("announces loading without exposing untranslated screen content", () => {
    render(<ScreenTranslationGate state="loading" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading this screen");
  });

  it("keeps an unclassified projection failure cause-neutral", () => {
    render(<ScreenTranslationGate state="retry" onRetry={() => undefined} />);
    expect(screen.getByText("We could not load this screen in your selected language.")).toBeInTheDocument();
    expect(screen.getByText("Retry the translation request. If it still fails, ask an administrator to check access and publication status.")).toBeInTheDocument();
    expect(screen.queryByText(/not available in your selected language yet/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ask an administrator to publish this screen/i)).not.toBeInTheDocument();
  });

  it("offers one retry action when published copy is unavailable", () => {
    const onRetry = vi.fn();
    render(<ScreenTranslationGate state="retry" onRetry={onRetry} />);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
