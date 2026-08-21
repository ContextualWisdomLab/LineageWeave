import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CustomerMasterEntity, RelatedNode } from "../api";
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

describe("CustomerMasterTree", () => {
  it("exposes hierarchy metadata and the complete WAI-ARIA navigation contract", async () => {
    render(
      <CustomerMasterTree
        entities={hierarchy}
        loadRelated={async () => []}
        onOpenPost={() => undefined}
      />,
    );

    expect(screen.getByRole("tree")).toBeInTheDocument();
    const group = screen.getByRole("treeitem", { name: /Demo Group/ });
    const company = screen.getByRole("treeitem", { name: /Demo Company/ });
    const plant = screen.getByRole("treeitem", { name: /Demo Plant/ });
    expect(group).toHaveAttribute("aria-level", "1");
    expect(group).toHaveAttribute("aria-posinset", "1");
    expect(group).toHaveAttribute("aria-setsize", "1");
    expect(company).toHaveAttribute("aria-level", "2");
    expect(plant).toHaveAttribute("aria-level", "3");

    group.focus();
    fireEvent.keyDown(group, { key: "ArrowDown" });
    expect(company).toHaveFocus();
    fireEvent.keyDown(company, { key: "ArrowDown" });
    expect(plant).toHaveFocus();
    fireEvent.keyDown(plant, { key: "ArrowUp" });
    expect(company).toHaveFocus();
    fireEvent.keyDown(company, { key: "Home" });
    expect(group).toHaveFocus();
    fireEvent.keyDown(group, { key: "End" });
    expect(plant).toHaveFocus();
    fireEvent.keyDown(plant, { key: "ArrowLeft" });
    expect(company).toHaveFocus();

    fireEvent.keyDown(company, { key: "ArrowLeft" });
    await waitFor(() =>
      expect(screen.queryByRole("treeitem", { name: /Demo Plant/ })).not.toBeInTheDocument(),
    );
    expect(company).toHaveAttribute("aria-expanded", "false");
    fireEvent.keyDown(company, { key: "ArrowRight" });
    expect(await screen.findByRole("treeitem", { name: /Demo Plant/ })).toBeInTheDocument();
    expect(company).toHaveAttribute("aria-expanded", "true");
    fireEvent.keyDown(company, { key: "ArrowRight" });
    expect(screen.getByRole("treeitem", { name: /Demo Plant/ })).toHaveFocus();
  });

  it("uses branch disclosure independently from evidence selection", async () => {
    render(
      <CustomerMasterTree
        entities={hierarchy}
        loadRelated={async () => []}
        onOpenPost={() => undefined}
      />,
    );

    const group = screen.getByRole("treeitem", { name: /Demo Group/ });
    const branchToggle = group.querySelector("[data-customer-branch-toggle]");
    expect(branchToggle).not.toBeNull();
    await userEvent.click(branchToggle as HTMLElement);
    expect(group).toHaveAttribute("aria-expanded", "false");
    expect(group).toHaveAttribute("aria-selected", "false");
    expect(screen.queryByRole("treeitem", { name: /Demo Company/ })).not.toBeInTheDocument();
    await userEvent.click(branchToggle as HTMLElement);
    expect(await screen.findByRole("treeitem", { name: /Demo Company/ })).toBeInTheDocument();
  });

  it("opens source-backed posts outside the tree with keyboard activation", async () => {
    const onOpenPost = vi.fn();
    const related: RelatedNode[] = [
      {
        node_id: "post-1",
        node_type_code: "node_post",
        relevance: 1,
        label: "Customer escalation",
        ontology_label: "Post",
        post_body_excerpt: "Escalation evidence",
        post_body_truncated: false,
      },
    ];
    const loadRelated = vi.fn(async () => related);
    render(
      <CustomerMasterTree
        entities={hierarchy}
        loadRelated={loadRelated}
        onOpenPost={onOpenPost}
      />,
    );

    const tree = screen.getByRole("tree");
    const company = screen.getByRole("treeitem", { name: /Demo Company/ });
    company.focus();
    fireEvent.keyDown(company, { key: "Enter" });
    expect(loadRelated).toHaveBeenCalledWith("company");
    expect(company).toHaveAttribute("aria-selected", "true");
    const evidence = await screen.findByRole("region", {
      name: "Related posts: Demo Company",
    });
    expect(tree).not.toContainElement(evidence);
    expect(company).toHaveAttribute("aria-controls", evidence.id);
    expect(
      within(evidence).getByRole("button", {
        name: "Open related post: Customer escalation",
      }),
    ).toHaveTextContent("Escalation evidence");
    expect(screen.getByRole("treeitem", { name: /Demo Plant/ })).toBeInTheDocument();

    fireEvent.keyDown(company, { key: " " });
    expect(
      screen.queryByRole("region", { name: "Related posts: Demo Company" }),
    ).not.toBeInTheDocument();
    fireEvent.keyDown(company, { key: "Enter" });
    const reopenedEvidence = await screen.findByRole("region", {
      name: "Related posts: Demo Company",
    });
    expect(loadRelated).toHaveBeenCalledTimes(1);

    await userEvent.click(
      within(reopenedEvidence).getByRole("button", {
        name: "Open related post: Customer escalation",
      }),
    );
    expect(onOpenPost).toHaveBeenCalledWith("post-1");
  });

  it("does not let a stale entity request overwrite newly selected evidence", async () => {
    let resolveGroup: ((value: RelatedNode[]) => void) | undefined;
    const groupRequest = new Promise<RelatedNode[]>((resolve) => {
      resolveGroup = resolve;
    });
    const loadRelated = vi.fn((entityId: string) =>
      entityId === "group" ? groupRequest : Promise.resolve([]),
    );
    render(
      <CustomerMasterTree
        entities={hierarchy}
        loadRelated={loadRelated}
        onOpenPost={() => undefined}
      />,
    );

    await userEvent.click(screen.getByRole("treeitem", { name: /Demo Group/ }));
    await userEvent.click(screen.getByRole("treeitem", { name: /Demo Company/ }));
    resolveGroup?.([
      {
        node_id: "stale-post",
        node_type_code: "node_post",
        relevance: 1,
        label: "Stale group post",
        ontology_label: "Post",
      },
    ]);

    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: "Related posts: Demo Company" }),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText("Stale group post")).not.toBeInTheDocument();
  });

  it("fails a related-post request closed without hiding the customer", async () => {
    render(
      <CustomerMasterTree
        entities={hierarchy}
        loadRelated={async () => {
          throw new Error("network unavailable");
        }}
        onOpenPost={() => undefined}
      />,
    );

    await userEvent.click(screen.getByRole("treeitem", { name: /Demo Plant/ }));
    expect(await screen.findByText("No linked posts yet.")).toBeInTheDocument();
    expect(screen.getByRole("treeitem", { name: /Demo Plant/ })).toBeInTheDocument();
  });

  it("keeps malformed hierarchy members visible and marks the relation unresolved", () => {
    render(
      <CustomerMasterTree
        entities={[
          entity("a", "Cycle A", "b"),
          entity("b", "Cycle B", "a"),
          entity("self", "Self Parent", "self"),
          entity("orphan", "Missing Parent", "missing"),
        ]}
        loadRelated={async () => []}
        onOpenPost={() => undefined}
      />,
    );

    expect(screen.getAllByRole("treeitem")).toHaveLength(4);
    expect(screen.getByRole("treeitem", { name: /Cycle A.*unresolved/i })).toBeInTheDocument();
    expect(screen.getByRole("treeitem", { name: /Cycle B.*unresolved/i })).toBeInTheDocument();
    expect(screen.getByRole("treeitem", { name: /Self Parent.*unresolved/i })).toBeInTheDocument();
    expect(screen.getByRole("treeitem", { name: /Missing Parent.*unresolved/i })).toBeInTheDocument();
  });
});
