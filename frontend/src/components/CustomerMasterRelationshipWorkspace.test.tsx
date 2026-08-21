import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CustomerMasterEntity, RelatedNode } from "../api";
import { getCustomerMasterWorkspaceCopy } from "../customerMasterWorkspace";
import { SUPPORTED_LOCALES } from "../i18n";
import { CustomerMasterTree } from "./CustomerMasterTree";

function entity(
  id: string,
  name: string,
  parentEntityId: string | null = null,
  level: "Group" | "Company" | "Plant" = "Company",
): CustomerMasterEntity {
  return {
    corporate_entity_id: id,
    corporate_entity_code: id.toUpperCase(),
    entity_name: name,
    entity_level_code: level.toLowerCase(),
    entity_level_label: level,
    parent_entity_id: parentEntityId,
  };
}

const hierarchy = [
  entity("group", "Demo Group", null, "Group"),
  entity("company", "Demo Company", "group", "Company"),
  entity("plant", "Demo Plant", "company", "Plant"),
];

function post(entityId: string): RelatedNode {
  return {
    node_id: `post-${entityId}`,
    node_type_code: "node_post",
    relevance: 1,
    label: `${entityId} evidence`,
    post_body_excerpt: `${entityId} source-backed excerpt`,
    post_body_truncated: false,
  };
}

describe("Customer Master three-pane workspace", () => {
  it("centers the selected customer between hierarchy and source-backed evidence", async () => {
    const loadRelated = vi.fn(async (entityId: string) => [post(entityId)]);
    render(
      <CustomerMasterTree
        entities={hierarchy}
        loadRelated={loadRelated}
        onOpenPost={() => undefined}
      />,
    );

    const workspace = screen.getByRole("heading", { name: "Choose a customer in scope" })
      .closest(".customer-master-relationship-workspace");
    expect(workspace).not.toBeNull();
    expect(workspace?.querySelectorAll(".customer-master-workspace-pane")).toHaveLength(3);

    await userEvent.click(screen.getByRole("treeitem", { name: /Demo Company/ }));

    const focusPane = screen.getByRole("heading", { name: "Customer relationship focus" })
      .closest("section");
    expect(focusPane).not.toBeNull();
    expect(within(focusPane as HTMLElement).getByRole("heading", { name: "Demo Company" }))
      .toBeInTheDocument();
    expect(
      within(focusPane as HTMLElement).getByRole("button", {
        name: "Center this customer: Demo Group",
      }),
    ).toBeInTheDocument();
    expect(
      within(focusPane as HTMLElement).getByRole("button", {
        name: "Center this customer: Demo Plant",
      }),
    ).toBeInTheDocument();

    const evidence = await screen.findByRole("region", {
      name: "Related posts: Demo Company",
    });
    expect(screen.getByRole("tree")).not.toContainElement(evidence);
    expect(within(evidence).getByText("company source-backed excerpt")).toBeInTheDocument();
    expect(loadRelated).toHaveBeenCalledWith("company");
  });

  it("recenters through relationship cards without inventing hidden relations", async () => {
    render(
      <CustomerMasterTree
        entities={hierarchy}
        loadRelated={async (entityId) => [post(entityId)]}
        onOpenPost={() => undefined}
      />,
    );

    await userEvent.click(screen.getByRole("treeitem", { name: /Demo Company/ }));
    await userEvent.click(
      screen.getByRole("button", { name: "Center this customer: Demo Group" }),
    );

    const focusPane = screen.getByRole("heading", { name: "Customer relationship focus" })
      .closest("section");
    expect(
      within(focusPane as HTMLElement).getByRole("heading", { name: "Demo Group" }),
    ).toBeInTheDocument();
    expect(within(focusPane as HTMLElement).getByText(
      "No parent organization is visible in the authorized scope.",
    )).toBeInTheDocument();
    expect(
      within(focusPane as HTMLElement).getByRole("button", {
        name: "Center this customer: Demo Company",
      }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Related posts: Demo Group" }))
      .toBeInTheDocument();
  });

  it("keeps the customer selected while the evidence pane is closed and reopened from cache", async () => {
    const loadRelated = vi.fn(async (entityId: string) => [post(entityId)]);
    render(
      <CustomerMasterTree
        entities={hierarchy}
        loadRelated={loadRelated}
        onOpenPost={() => undefined}
      />,
    );

    const company = screen.getByRole("treeitem", { name: /Demo Company/ });
    await userEvent.click(company);
    expect(await screen.findByRole("region", { name: "Related posts: Demo Company" }))
      .toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Close linked evidence" }));
    expect(screen.queryByRole("region", { name: "Related posts: Demo Company" }))
      .not.toBeInTheDocument();
    expect(company).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Demo Company" })).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("button", { name: "Open linked evidence" })[0]);
    expect(await screen.findByRole("region", { name: "Related posts: Demo Company" }))
      .toBeInTheDocument();
    expect(loadRelated).toHaveBeenCalledTimes(1);
  });

  it("supports deterministic selected and unselected Storybook states without fabricating evidence", () => {
    const loadRelated = vi.fn(async () => []);
    const { rerender } = render(
      <CustomerMasterTree
        entities={hierarchy}
        initialSelectedEntityId="company"
        loadRelated={loadRelated}
        onOpenPost={() => undefined}
      />,
    );

    expect(screen.getByRole("heading", { name: "Demo Company" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Related posts: Demo Company" }))
      .not.toBeInTheDocument();
    expect(loadRelated).not.toHaveBeenCalled();

    rerender(
      <CustomerMasterTree
        entities={hierarchy}
        initialSelectedEntityId="outside-authorized-scope"
        loadRelated={loadRelated}
        onOpenPost={() => undefined}
      />,
    );
    expect(screen.queryByRole("heading", { name: "Demo Company" }))
      .not.toBeInTheDocument();
    expect(screen.getByText(
      "Select a customer from the hierarchy to center its relationships.",
    )).toBeInTheDocument();
  });

  it("explains leaf and unresolved relationship boundaries in the center pane", async () => {
    render(
      <CustomerMasterTree
        entities={[entity("orphan", "Unresolved Plant", "outside", "Plant")]}
        loadRelated={async () => []}
        onOpenPost={() => undefined}
      />,
    );

    await userEvent.click(screen.getByRole("treeitem", { name: /Unresolved Plant.*unresolved/i }));
    const focusPane = screen.getByRole("heading", { name: "Customer relationship focus" })
      .closest("section");
    expect(within(focusPane as HTMLElement).getByText(
      "This hierarchy relation is unresolved. Review the source data before treating it as authoritative.",
    )).toBeInTheDocument();
    expect(within(focusPane as HTMLElement).getByText(
      "No parent organization is visible in the authorized scope.",
    )).toBeInTheDocument();
    expect(within(focusPane as HTMLElement).getByText(
      "No direct child organization is visible in the authorized scope.",
    )).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("No linked posts yet.")).toBeInTheDocument());
  });

  it("does not show a malformed self-parent as an authoritative parent", async () => {
    render(
      <CustomerMasterTree
        entities={[entity("self", "Self Parent", "self", "Company")]}
        loadRelated={async () => []}
        onOpenPost={() => undefined}
      />,
    );

    await userEvent.click(screen.getByRole("treeitem", { name: /Self Parent.*unresolved/i }));
    const focusPane = screen.getByRole("heading", { name: "Customer relationship focus" })
      .closest("section");
    expect(within(focusPane as HTMLElement).getByText(
      "No parent organization is visible in the authorized scope.",
    )).toBeInTheDocument();
    expect(within(focusPane as HTMLElement).queryByRole("button", {
      name: "Center this customer: Self Parent",
    })).not.toBeInTheDocument();
  });
});

describe("Customer Master workspace localization", () => {
  it("provides the same complete copy contract for all product locales", () => {
    const englishKeys = Object.keys(getCustomerMasterWorkspaceCopy("en")).sort();
    for (const locale of SUPPORTED_LOCALES) {
      const localized = getCustomerMasterWorkspaceCopy(locale);
      expect(Object.keys(localized).sort(), locale).toEqual(englishKeys);
      expect(Object.values(localized).every((value) => value.trim().length > 0), locale).toBe(true);
    }
  });
});
