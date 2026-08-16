import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { RelatedNode } from "./api";
import { RelatedNodeChip } from "./RelatedNodeChip";
import { relatedNodeAriaLabel, relatedNodeCaption } from "./relatedNodeCaption";

function node(partial: Partial<RelatedNode> & Pick<RelatedNode, "node_type_code">): RelatedNode {
  return {
    node_id: "node-1",
    relevance: 0.4,
    ...partial,
  };
}

describe("RelatedNodeChip", () => {
  it("keeps the visible caption inside the accessible name", () => {
    const priya = node({
      node_type_code: "node_person",
      label: "Priya Nair",
      person_side_label: "Counterparty",
      affiliation_ambiguous: true,
    });
    const caption = relatedNodeCaption(priya);
    expect(caption).toBe("Priya Nair, multiple organizations (Counterparty)");
    render(<RelatedNodeChip node={priya} onSelect={() => undefined} />);
    expect(
      screen.getByRole("button", { name: relatedNodeAriaLabel(priya, caption) }),
    ).toHaveTextContent(caption);
  });

  it("continues the walk when the unique-org chip is clicked", async () => {
    const ada = node({
      node_id: "ada-1",
      node_type_code: "node_person",
      label: "Ada West",
      person_side_label: "Our side",
      affiliation_organization_name: "Demo Corp",
    });
    const onSelect = vi.fn();
    render(<RelatedNodeChip node={ada} onSelect={onSelect} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Related nodes for Ada West, Demo Corp (Our side)" }),
    );
    expect(onSelect).toHaveBeenCalledWith(ada);
  });

  it("opens the related post from the title-only chip", async () => {
    const post = node({
      node_id: "post-1",
      node_type_code: "node_post",
      label: "Linked post",
      ontology_label: "Post",
    });
    const onSelect = vi.fn();
    render(<RelatedNodeChip node={post} onSelect={onSelect} />);
    await userEvent.click(screen.getByRole("button", { name: "Open related post: Linked post" }));
    expect(onSelect).toHaveBeenCalledWith(post);
  });
});
