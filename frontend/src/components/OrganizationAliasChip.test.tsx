import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OrganizationAliasChip } from "./OrganizationAliasChip";
import { organizationAliasCaption } from "./organizationAliasCaption";

describe("organizationAliasCaption", () => {
  it("puts the unique companion in parentheses", () => {
    expect(organizationAliasCaption("Demo Corp", "DC")).toBe("Demo Corp (DC)");
    expect(organizationAliasCaption("Demo Corp", null)).toBe("Demo Corp");
    expect(organizationAliasCaption("Demo Corp", "  ")).toBe("Demo Corp");
  });
});

describe("OrganizationAliasChip", () => {
  it("opens the cataloged organization when the buyer clicks the chip", async () => {
    const onSelect = vi.fn();
    render(
      <OrganizationAliasChip
        displayName="Demo Corp"
        organizationAlias="DC"
        ariaLabel="Affiliate org: Demo Corp (DC)"
        onSelect={onSelect}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Affiliate org: Demo Corp (DC)" }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Affiliate org: Demo Corp (DC)" })).toHaveTextContent(
      "Demo Corp (DC)",
    );
  });

  it("keeps the catalog name when no companion is bound", () => {
    render(
      <OrganizationAliasChip
        displayName="Northridge Grid"
        ariaLabel="Affiliate org: Northridge Grid"
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: "Affiliate org: Northridge Grid" })).toHaveTextContent(
      "Northridge Grid",
    );
  });
});
