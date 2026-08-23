import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminPanel } from "./AdminPanel";
import * as api from "../api";

describe("AdminPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("ignores unchanged and whitespace-only submissions", async () => {
    const updateSpy = vi.spyOn(api, "updateTenantConfig");
    render(
      <AdminPanel currentBrandName="LineageWeave" onBrandNameChange={vi.fn()} accessToken="token" />,
    );
    const button = screen.getByRole("button", { name: "Save settings" });
    const input = screen.getByRole("textbox", { name: "Tenant brand name" });
    const form = button.closest("form");

    expect(button).toBeDisabled();
    fireEvent.submit(form!);
    await userEvent.clear(input);
    await userEvent.type(input, "   ");
    expect(button).toBeDisabled();
    fireEvent.submit(form!);
    expect(updateSpy).not.toHaveBeenCalled();
  });

  it("saves a changed brand name and reports it back to the caller", async () => {
    const timeoutSpy = vi.spyOn(globalThis, "setTimeout");
    const updateSpy = vi
      .spyOn(api, "updateTenantConfig")
      .mockResolvedValue({ brandName: "Renamed Corp" });
    const onBrandNameChange = vi.fn();
    render(
      <AdminPanel currentBrandName="LineageWeave" onBrandNameChange={onBrandNameChange} accessToken="token" />,
    );

    const input = screen.getByRole("textbox", { name: "Tenant brand name" });
    await userEvent.clear(input);
    await userEvent.type(input, "Renamed Corp");
    await userEvent.click(screen.getByRole("button", { name: "Save settings" }));

    expect(updateSpy).toHaveBeenCalledWith("token", "Renamed Corp");
    expect(await screen.findByRole("status")).toHaveTextContent("Settings saved!");
    expect(onBrandNameChange).toHaveBeenCalledWith("Renamed Corp");
    const timeoutIndex = timeoutSpy.mock.calls.findIndex((call) => call[1] === 3000);
    expect(timeoutIndex).toBeGreaterThanOrEqual(0);
    clearTimeout(timeoutSpy.mock.results[timeoutIndex].value);
    act(() => (timeoutSpy.mock.calls[timeoutIndex][0] as () => void)());
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("shows an error and leaves the form editable when the save fails", async () => {
    vi.spyOn(api, "updateTenantConfig").mockRejectedValue(new Error("Failed to update settings"));
    render(
      <AdminPanel currentBrandName="LineageWeave" onBrandNameChange={vi.fn()} accessToken="token" />,
    );

    const input = screen.getByRole("textbox", { name: "Tenant brand name" });
    await userEvent.clear(input);
    await userEvent.type(input, "Renamed Corp");
    await userEvent.click(screen.getByRole("button", { name: "Save settings" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Failed to update settings");
    expect(screen.getByRole("button", { name: "Save settings" })).not.toBeDisabled();
  });

  it("uses the actionable fallback when a failure has no message", async () => {
    vi.spyOn(api, "updateTenantConfig").mockRejectedValue(new Error(""));
    render(
      <AdminPanel currentBrandName="LineageWeave" onBrandNameChange={vi.fn()} accessToken="token" />,
    );

    const input = screen.getByRole("textbox", { name: "Tenant brand name" });
    await userEvent.clear(input);
    await userEvent.type(input, "Renamed Corp");
    await userEvent.click(screen.getByRole("button", { name: "Save settings" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Failed to update settings");
  });
});
