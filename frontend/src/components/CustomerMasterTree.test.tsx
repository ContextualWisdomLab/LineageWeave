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
  it("exposes hierarchy levels and WAI-ARIA arrow-key navigation", async () => {
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
    expect(company).toHaveAttribute("aria-level", "2");
    expect(plant).toHaveAttribute("aria-level", "3");

    group.focus();
    fireEvent.keyDown(group, { key: "ArrowRight" });
    expect(company).toHaveFocus();
    fireEvent.keyDown(company, { key: "ArrowRight" });
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
  });

  it("opens source-backed posts outside the tree without changing hierarchy disclosure", async () => {
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
    await userEvent.click(company);
    expect(loadRelated).toHaveBeenCalledWith("company");
    expect(company).toHaveAttribute("aria-selected", "true");
    const evidence = await screen.findByRole("region", {
      name: "Related posts: Demo Company",
    });
    expect(tree).not.toContainElement(evidence);
    const post = within(evidence).getByRole("button", {
      name: "Open related post: Customer escalation",
    });
    expect(post).toHaveTextContent("Escalation evidence");
    expect(screen.getByRole("treeitem", { name: /Demo Plant/ })).toBeInTheDocument();

    await userEvent.click(post);
    expect(onOpenPost).toHaveBeenCalledWith("post-1");
  });

  it("does not let a stale entity request overwrite the newly opened evidence", async () => {
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
