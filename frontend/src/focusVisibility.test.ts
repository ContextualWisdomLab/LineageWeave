import { describe, expect, it, vi } from "vitest";
import { isFocusableVisible } from "./focusVisibility";

describe("isFocusableVisible", () => {
  it("requests the current opacity and visibility property checks", () => {
    const button = document.createElement("button");
    const checkVisibility = vi.fn(() => true);
    button.checkVisibility = checkVisibility;

    expect(isFocusableVisible(button)).toBe(true);
    expect(checkVisibility).toHaveBeenCalledWith({
      opacityProperty: true,
      visibilityProperty: true,
      checkOpacity: true,
      checkVisibilityCSS: true,
    });
  });

  it("excludes controls inside collapsed disclosure content", () => {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    const button = document.createElement("button");
    details.append(summary, button);
    expect(isFocusableVisible(summary)).toBe(true);
    expect(isFocusableVisible(button)).toBe(false);
  });
});
