import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AdminPanel } from "./AdminPanel";
import * as api from "../api";

describe("AdminPanel", () => {
  it("disables save until the brand name actually changes", () => {
    render(
      <AdminPanel currentBrandName="LineageWeave" onBrandNameChange={vi.fn()} accessToken="token" />,
    );
    expect(screen.getByRole("button", { name: "Save settings" })).toBeDisabled();
  });

  it("saves a changed brand name and reports it back to the caller", async () => {
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
    expect(await screen.findByText("Settings saved!")).toBeInTheDocument();
    expect(onBrandNameChange).toHaveBeenCalledWith("Renamed Corp");
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

    expect(await screen.findByText("Failed to update settings")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save settings" })).not.toBeDisabled();
  });
});
